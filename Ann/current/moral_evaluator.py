"""
Moral Evaluator — hybrid (rules + LLM) risk classifier for Ann.

Implements moral_module_spec.md:
  - §9   Decision pipeline (interpret → classify → choose mode → rationale → audit)
  - §10  Response modes (comply / safeguards / clarify / partial refusal / refuse / escalate)
  - §11  Risk assessment, classifier output (§11.2), fallback (§11.3), thresholds (§11.4)
  - §12  Harm categories
  - §18  Human review triggers
  - §19  Local escalation levels E0–E5  +  §19.2 emergency response
  - §21  Audit log schema
  - §26  MoralModuleOutput interface

Design:
  - Hard prohibited / emergency / high-risk cases are caught by a deterministic
    rules engine (fast, works offline).
  - Only the *ambiguous sensitive band* (a MEDIUM keyword fired) is refined by a
    structured LLM classifier, when ``call_llm`` is available. Obvious-benign and
    hard cases never call the LLM (latency control, §11.1 "keyword as preliminary
    signal").
  - When ``call_llm`` is None (Ollama offline/disabled) the evaluator degrades to
    pure rules with identical decisions — no crash, no weakening.

The spec (moral_module_spec.md) must NOT be modified. This file implements it.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"


class Decision(Enum):
    COMPLY = "comply"
    COMPLY_WITH_SAFEGUARDS = "comply_with_safeguards"
    CLARIFY = "clarify"
    PARTIAL_REFUSAL = "partial_refusal"
    REFUSE = "refuse"
    ESCALATE_OR_PAUSE = "escalate_or_pause"


@dataclass
class MoralResult:
    """spec §26 MoralModuleOutput. First four fields kept for backward compatibility."""

    risk_level: RiskLevel
    decision: Decision
    rationale: str
    confidence: float  # 0.0–1.0
    # --- spec §26 additions (defaults keep existing constructors working) ---
    escalation_level: str = "E0"           # E0–E5 (§19)
    harm_categories: list = field(default_factory=list)         # §12
    affected_parties: list = field(default_factory=list)        # §11.2
    inaction_risks: list = field(default_factory=list)          # §6 / §11.2
    policy_sources_triggered: list = field(default_factory=list)  # §11.2
    safeguards: list = field(default_factory=list)              # §10.2
    requires_human_review: bool = False    # §18
    audit_log: dict | None = None          # §21


# ---------------------------------------------------------------------------
# Rule pattern tables — derived from moral_module_spec.md §12 (Harm Categories)
# ---------------------------------------------------------------------------

# (pattern, harm categories) — §12
_PROHIBITED_RAW = [
    (r"how to (make|build|synthesize|create) (a |an )?(bomb|explosive|weapon|poison|nerve agent)",
     ["violence_or_weaponization", "physical_harm"]),
    (r"step[s]? (to|for) (kill|murder|assassinate) (someone|a person)",
     ["violence_or_weaponization", "physical_harm"]),
    (r"write (malware|ransomware|keylogger|trojan|virus|worm)",
     ["cyber_abuse_or_unauthorized_access"]),
    (r"child (porn|sexual abuse material|nude|naked)",
     ["sexual_exploitation", "child_safety_risk"]),
    (r"underage (sex|nude|porn|sexual)",
     ["sexual_exploitation", "child_safety_risk"]),
    (r"(hack into|gain unauthorized access to) (a |an )?(system|server|account|network)",
     ["cyber_abuse_or_unauthorized_access"]),
    (r"(steal|exfiltrate) (credentials|passwords|credit card|personal data) (from|of)",
     ["identity_theft_or_impersonation", "financial_fraud_or_coercion"]),
    (r"(create|write|generate) a? ?phishing (email|page|site|message)",
     ["identity_theft_or_impersonation", "misinformation_or_deception"]),
]

# §19.2 emergency — user (or a nearby person) appears to be at imminent risk.
_EMERGENCY_RAW = [
    r"\b(kill myself|killing myself|end my life|ending my life|take my own life|"
    r"want to die|wanna die|hurt myself|harm myself|self.?harm|suicidal|commit suicide|"
    r"overdose|overdosing)\b",
    r"\b(he|she|they|someone)\b.{0,20}\b(going to|about to|trying to)\b.{0,12}"
    r"\b(kill|hurt|attack|stab|shoot)\b.{0,10}\b(me|us)\b",
    r"\b(can'?t breathe|cannot breathe|heart attack|having a stroke|bleeding out|"
    r"overdosed|not breathing|unconscious)\b",
]

# §18 high-risk / consequential — (pattern, harm categories, domain)
_HIGH_RAW = [
    (r"\b(deny|reject|discriminate)\b.{0,30}\b(loan|applicant|tenant|employee)\b",
     ["discrimination_or_exclusion", "financial_fraud_or_coercion"], "financial"),
    (r"\bmedical diagnosis\b", ["physical_harm"], "medical"),
    (r"\bprescribe\b", ["physical_harm"], "medical"),
    (r"\b(minor|child)\b.{0,20}\b(abused|exploited|trafficked)\b",
     ["child_safety_risk"], "child_safety"),
]

# §10.2 sensitive band — keyword preliminary signal (§11.1)
_MEDIUM_RAW = [
    (r"\b(symptom[s]?|medication|drug dosage|disease|diagnos|medical note[s]?)\b",
     ["physical_harm"], "medical"),
    (r"\b(personal data|private address|phone number|social security)\b",
     ["privacy_invasion"], None),
    (r"\b(race|ethnicity|gender identity|sexual orientation|religion|political belief)\b",
     ["discrimination_or_exclusion"], None),
]

_PROHIBITED = [(re.compile(p, re.IGNORECASE), cats) for p, cats in _PROHIBITED_RAW]
_EMERGENCY = [re.compile(p, re.IGNORECASE) for p in _EMERGENCY_RAW]
_HIGH = [(re.compile(p, re.IGNORECASE), cats, dom) for p, cats, dom in _HIGH_RAW]
_MEDIUM = [(re.compile(p, re.IGNORECASE), cats, dom) for p, cats, dom in _MEDIUM_RAW]


# ---------------------------------------------------------------------------
# §21 audit record (privacy-preserving / redacted)
# ---------------------------------------------------------------------------

def build_audit_log(result: "MoralResult", detected_intent: str) -> dict:
    """
    Build a redacted §21 audit record. Stores a generalized intent label and the
    risk fields — never the full user message (data minimization, §16).
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": uuid.uuid4().hex[:12],
        "risk_level": result.risk_level.value,
        "detected_intent": detected_intent,
        "affected_parties": result.affected_parties,
        "harm_categories": result.harm_categories,
        "inaction_risks": result.inaction_risks,
        "principles_considered": ["human_welfare", "autonomy", "privacy", "truthfulness"],
        "policy_sources_triggered": result.policy_sources_triggered,
        "risk_confidence": round(result.confidence, 2),
        "decision": result.decision.value,
        "local_escalation_level": result.escalation_level,
        "rationale": result.rationale,
        "safeguards_applied": result.safeguards,
        "human_review_required": result.requires_human_review,
        "data_minimization_applied": True,
    }


# ---------------------------------------------------------------------------
# LLM structured classifier (§11.2) — JSON contract
# ---------------------------------------------------------------------------

_CLASSIFIER_PROMPT = (
    "You are a safety risk classifier. Classify the user request below.\n"
    "Respond ONLY with valid JSON, no prose, using exactly this schema:\n"
    '{"risk_level": "low|medium|high|prohibited", "confidence": 0.0-1.0, '
    '"harm_categories": ["..."], "affected_parties": ["..."], '
    '"inaction_risks": ["..."], "partial_refusal": true|false, "rationale": "short"}\n'
    "Guidance: benign educational, fictional, or defensive requests are low/medium, "
    "not prohibited. 'high' = significantly affects rights, safety, health, finances, "
    "or essential services. 'prohibited' = directly enables serious harm, abuse, "
    "illegality, exploitation, or unauthorized access. partial_refusal = true only when "
    "one specific sub-request is unsafe but the rest can be answered safely.\n\n"
    "User request: {text}"
)


def _parse_llm_json(raw: str) -> dict | None:
    """Extract the first JSON object from an LLM reply; return None on failure."""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None


_VALID_RISK = {"low": RiskLevel.LOW, "medium": RiskLevel.MEDIUM,
               "high": RiskLevel.HIGH, "prohibited": RiskLevel.PROHIBITED}


def _escalation_for(decision: Decision, domains: set[str]) -> str:
    """Map a decision (+ domain context) to a local escalation level E0–E5 (§19)."""
    if decision == Decision.REFUSE:
        return "E5"
    if decision == Decision.ESCALATE_OR_PAUSE:
        if domains & {"medical", "self_harm", "child_safety"}:
            return "E4"   # professional / emergency help
        if domains & {"financial", "employment", "housing", "legal"}:
            return "E3"   # second human decision-maker
        return "E1"       # confirm intent / authority
    if decision == Decision.CLARIFY:
        return "E1"
    if decision == Decision.PARTIAL_REFUSAL:
        return "E2"       # safer path
    if decision == Decision.COMPLY_WITH_SAFEGUARDS:
        return "E2"
    return "E0"


class MoralEvaluator:
    """
    Evaluates user input against the moral module specification.

    spec_path is accepted for forward-compatibility (embedding the spec into a
    future fine-grained classifier). The rule engine does not read it.
    """

    def __init__(self, spec_path: Path | None = None) -> None:
        self.spec_path = spec_path  # reserved

    # ------------------------------------------------------------------
    def evaluate(
        self,
        text: str,
        *,
        call_llm: Callable[[str], str] | None = None,
        images: list | None = None,
        policy=None,
    ) -> MoralResult:
        """
        Run the §9 decision pipeline and return a §26 MoralModuleOutput.

        Args:
            text:     The user's request.
            call_llm: Optional synchronous LLM callable for the §11.1 hybrid
                      refinement of ambiguous sensitive cases. None → pure rules.
            images:   Optional attached image paths. Image content cannot be
                      silently treated as safe (§15) → forces safeguards.
            policy:   Optional MoralPolicy. None → safe defaults.
        """
        from moral_policy import MoralPolicy  # local import avoids a cycle at import time

        if policy is None:
            policy = MoralPolicy()

        # Master kill-switch (operator/user disabled the layer) → comply.
        if not policy.enabled:
            return self._finalize(
                MoralResult(RiskLevel.LOW, Decision.COMPLY,
                            "Moral layer disabled by configuration.", 0.90,
                            policy_sources_triggered=["operator"]),
                policy, images, "moral-layer-disabled",
            )

        # --- 1. Hard prohibition (§12) — enabling severe harm → refuse, no LLM ---
        for pattern, cats in _PROHIBITED:
            if pattern.search(text):
                res = MoralResult(
                    RiskLevel.PROHIBITED, Decision.REFUSE,
                    "This request matches a hard-prohibited harm category and cannot be fulfilled.",
                    0.95, harm_categories=cats, requires_human_review=True,
                    policy_sources_triggered=["baseline", "law"],
                )
                return self._finalize(res, policy, images, "prohibited-harm-request")

        # --- 2. Emergency (§19.2) — user at imminent risk → safety guidance ---
        if policy.emergency.enabled and self._is_emergency(text, policy):
            res = MoralResult(
                RiskLevel.HIGH, Decision.ESCALATE_OR_PAUSE,
                self._emergency_rationale(policy), 0.90,
                escalation_level="E4",
                harm_categories=["self_harm", "physical_harm"],
                affected_parties=["user"],
                inaction_risks=["serious imminent physical harm if no help is sought"],
                requires_human_review=True,
                policy_sources_triggered=["baseline", "domain_norm"],
                safeguards=["did not provide any method or enabling detail",
                            "encouraged contacting emergency services / a trusted person"],
            )
            return self._finalize(res, policy, images, "imminent-safety-risk", domains={"self_harm"})

        # --- 3. High-risk / consequential (§18) → escalate or pause ---
        for pattern, cats, domain in _HIGH:
            if pattern.search(text):
                domains = {domain} if domain else set()
                res = MoralResult(
                    RiskLevel.HIGH, Decision.ESCALATE_OR_PAUSE,
                    "This request involves a high-risk domain (medical, legal, financial, "
                    "housing, or a consequential decision about another person). It needs "
                    "accountable human judgment; please confirm intent or consult a "
                    "qualified professional.",
                    0.82, harm_categories=cats, requires_human_review=True,
                    affected_parties=["affected_party"],
                    policy_sources_triggered=["baseline", "domain_norm"],
                )
                return self._finalize(res, policy, images, "high-risk-domain-request", domains=domains)

        # --- 4. Sensitive band (§10.2) — keyword preliminary signal ---
        medium_hit = None
        for pattern, cats, domain in _MEDIUM:
            if pattern.search(text):
                medium_hit = (cats, domain)
                break

        if medium_hit is not None:
            cats, domain = medium_hit
            domains = {domain} if domain else set()
            # §11.1 hybrid: refine the ambiguous case with the LLM when available.
            if policy.classifier == "hybrid" and call_llm is not None:
                refined = self._llm_refine(text, cats, domains, policy, call_llm)
                if refined is not None:
                    return self._finalize(refined, policy, images,
                                          "sensitive-request-refined", domains=domains)
            # Pure-rules / offline path → comply with safeguards.
            res = MoralResult(
                RiskLevel.MEDIUM, Decision.COMPLY_WITH_SAFEGUARDS,
                "This request touches a sensitive topic. Responding with appropriate care, "
                "privacy protection, and disclaimers.",
                0.72, harm_categories=cats, safeguards=["added disclaimers / privacy protection"],
                policy_sources_triggered=["baseline", "domain_norm"],
            )
            return self._finalize(res, policy, images, "sensitive-request", domains=domains)

        # --- 5. Default: low risk (§10.1) ---
        res = MoralResult(
            RiskLevel.LOW, Decision.COMPLY, "No significant risk detected.", 0.90,
            policy_sources_triggered=["baseline"],
        )
        return self._finalize(res, policy, images, "low-risk-request")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _is_emergency(self, text: str, policy) -> bool:
        triggers = policy.emergency.imminent_risk_triggers
        if triggers:
            low = text.lower()
            if any(t.lower() in low for t in triggers):
                return True
        return any(p.search(text) for p in _EMERGENCY)

    def _emergency_rationale(self, policy) -> str:
        label = policy.emergency.emergency_services_label
        lines = [
            "It sounds like you may be in danger or crisis. Your safety matters.",
            f"If you are in immediate danger, please contact {label} or a trusted person near you now.",
        ]
        for r in policy.emergency.crisis_resources:
            label_r = r.get("label", "Crisis support") if isinstance(r, dict) else str(r)
            contact = r.get("contact", "") if isinstance(r, dict) else ""
            lines.append(f"• {label_r}: {contact}".rstrip(": ").rstrip())
        if policy.emergency.local_only_mode and not policy.emergency.allow_external_contact:
            lines.append("(I can offer support and information here, but I cannot contact "
                         "anyone on your behalf.)")
        return "\n".join(lines)

    def _llm_refine(self, text: str, rule_cats: list, domains: set, policy,
                    call_llm: Callable[[str], str]) -> MoralResult | None:
        """§11.2 structured LLM refinement of a sensitive-band request. None on failure."""
        try:
            raw = call_llm(self._build_classifier_prompt(text))
        except Exception as exc:  # offline / timeout — caller falls back to rules
            logger.info("Moral LLM refine unavailable, using rules: %s", exc)
            return None
        data = _parse_llm_json(raw)
        if not isinstance(data, dict) or data.get("risk_level") not in _VALID_RISK:
            logger.info("Moral LLM refine returned unparseable output, using rules.")
            return None

        risk = _VALID_RISK[data["risk_level"]]
        # §11.4: cap effective confidence at 0.84 (calibration not validated).
        try:
            conf = max(0.0, min(0.84, float(data.get("confidence", 0.6))))
        except (TypeError, ValueError):
            conf = 0.6
        harm_categories = list(data.get("harm_categories") or rule_cats)
        affected = list(data.get("affected_parties") or [])
        inaction = list(data.get("inaction_risks") or [])
        partial = bool(data.get("partial_refusal", False))
        rationale = str(data.get("rationale") or "").strip() or "Refined by safety classifier."

        high_impact = bool(domains & set(policy.high_risk_domains))

        # --- map refined risk → decision (§10, §11.3, §11.4) ---
        if risk == RiskLevel.PROHIBITED:
            decision = Decision.REFUSE
        elif partial:
            decision = Decision.PARTIAL_REFUSAL
        elif conf < 0.60 and (high_impact or risk == RiskLevel.HIGH):
            # low confidence in a high-impact domain → don't gamble (§11.4)
            decision = Decision.ESCALATE_OR_PAUSE
        elif 0.40 <= conf <= 0.59:
            decision = Decision.CLARIFY
        elif risk == RiskLevel.HIGH:
            # high but with urgent inaction risk → assist carefully (§22 "chest pain")
            decision = (Decision.COMPLY_WITH_SAFEGUARDS if inaction
                        else Decision.ESCALATE_OR_PAUSE)
        else:
            # low / medium but a sensitive keyword fired → never plain comply (§11.3.3)
            decision = Decision.COMPLY_WITH_SAFEGUARDS

        safeguards = []
        if decision == Decision.COMPLY_WITH_SAFEGUARDS:
            safeguards = ["added disclaimers / privacy protection"]
        if decision == Decision.PARTIAL_REFUSAL:
            safeguards = ["declined the unsafe part; answered the safe part only"]

        res = MoralResult(
            risk_level=risk, decision=decision, rationale=rationale, confidence=conf,
            harm_categories=harm_categories, affected_parties=affected,
            inaction_risks=inaction, safeguards=safeguards,
            requires_human_review=decision in (Decision.REFUSE, Decision.ESCALATE_OR_PAUSE),
            policy_sources_triggered=["baseline", "classifier", "domain_norm"],
        )
        return res

    def _build_classifier_prompt(self, text: str) -> str:
        return _CLASSIFIER_PROMPT.replace("{text}", text)

    def _finalize(self, res: MoralResult, policy, images, intent: str,
                  domains: set | None = None) -> MoralResult:
        """Apply image-safeguard, escalation level, and audit-log population."""
        # §15 honesty: attached images are not independently screened here.
        if images:
            note = ("attached image content was not independently screened — "
                    "treat visual content with caution")
            if res.decision == Decision.COMPLY:
                res.decision = Decision.COMPLY_WITH_SAFEGUARDS
                res.risk_level = RiskLevel.MEDIUM
            if note not in res.safeguards:
                res.safeguards.append(note)

        # escalation level (respect any already-set non-default value, e.g. emergency E4)
        if res.escalation_level == "E0":
            res.escalation_level = _escalation_for(res.decision, domains or set())

        # §21 audit — redacted, medium-and-above, only when logging enabled.
        if (policy.logging.enabled and policy.logging.audit_medium_and_above
                and res.risk_level != RiskLevel.LOW):
            res.audit_log = build_audit_log(res, intent)
        return res
