"""
Moral Evaluator — rule-based risk classifier for Ann.

Implements a subset of moral_module_spec.md (Sections 9–12):
  - Prohibited risk  → Decision.REFUSE
  - High risk        → Decision.ESCALATE_OR_PAUSE
  - Medium risk      → Decision.COMPLY_WITH_SAFEGUARDS
  - Low risk         → Decision.COMPLY

The spec (moral_module_spec.md) must NOT be modified.
This file implements it; the spec defines it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"


class Decision(Enum):
    COMPLY = "comply"
    COMPLY_WITH_SAFEGUARDS = "comply_with_safeguards"
    CLARIFY = "clarify"           # NOTE: dead code — not returned by evaluate(); reserved for future LLM-based classifier
    PARTIAL_REFUSAL = "partial_refusal"  # NOTE: dead code — not returned by evaluate(); reserved for future LLM-based classifier
    REFUSE = "refuse"
    ESCALATE_OR_PAUSE = "escalate_or_pause"


@dataclass
class MoralResult:
    risk_level: RiskLevel
    decision: Decision
    rationale: str
    confidence: float  # 0.0–1.0


# ---------------------------------------------------------------------------
# Pattern tables derived from moral_module_spec.md §12 (Harm Categories)
# ---------------------------------------------------------------------------

_PROHIBITED_RAW = [
    # Weapons / physical harm
    r"how to (make|build|synthesize|create) (a |an )?(bomb|explosive|weapon|poison|nerve agent)",
    r"step[s]? (to|for) (kill|murder|assassinate) (someone|a person)",
    r"write (malware|ransomware|keylogger|trojan|virus|worm)",
    # Sexual exploitation of minors
    r"child (porn|sexual abuse material|nude|naked)",
    r"underage (sex|nude|porn|sexual)",
    # Cyber abuse
    r"(hack into|gain unauthorized access to) (a |an )?(system|server|account|network)",
    r"(steal|exfiltrate) (credentials|passwords|credit card|personal data) (from|of)",
    # Identity / fraud
    r"(create|write|generate) a? ?phishing (email|page|site|message)",
]

_HIGH_RAW = [
    # Self-harm / suicide
    r"\b(self.?harm|suicide method|how to (die|end my life)|overdose on \w+)\b",
    # Consequential decisions (§18: legal, medical, financial, housing)
    r"\b(deny|reject|discriminate).{0,30}(loan|applicant|tenant|employee)\b",
    r"\bmedical diagnosis\b",
    r"\bprescribe\b",
    # Requests involving minors in danger
    r"\b(minor|child).{0,20}(abused|exploited|trafficked)\b",
]

_MEDIUM_RAW = [
    # Medical / health info
    r"\b(symptom[s]?|medication|drug dosage|disease|diagnos|medical note[s]?)\b",
    # Privacy / personal data
    r"\b(personal data|private address|phone number|social security)\b",
    # Sensitive attributes (§13)
    r"\b(race|ethnicity|gender identity|sexual orientation|religion|political belief)\b",
]

_PROHIBITED = [re.compile(p, re.IGNORECASE) for p in _PROHIBITED_RAW]
_HIGH = [re.compile(p, re.IGNORECASE) for p in _HIGH_RAW]
_MEDIUM = [re.compile(p, re.IGNORECASE) for p in _MEDIUM_RAW]


class MoralEvaluator:
    """
    Evaluates user input against the moral module specification.

    spec_path is accepted for forward-compatibility (future: embed the spec
    into an LLM-based classifier). Currently unused by the rule engine.
    """

    def __init__(self, spec_path: Path | None = None) -> None:
        self.spec_path = spec_path  # reserved for future use

    def evaluate(self, text: str) -> MoralResult:
        # --- Hard-prohibition check (§12, highest priority) ---
        for pattern in _PROHIBITED:
            if pattern.search(text):
                return MoralResult(
                    risk_level=RiskLevel.PROHIBITED,
                    decision=Decision.REFUSE,
                    rationale=(
                        "This request matches a hard-prohibited harm category "
                        "and cannot be fulfilled."
                    ),
                    confidence=0.95,
                )

        # --- High-risk check (§18: requires human confirmation or professional) ---
        for pattern in _HIGH:
            if pattern.search(text):
                return MoralResult(
                    risk_level=RiskLevel.HIGH,
                    decision=Decision.ESCALATE_OR_PAUSE,
                    rationale=(
                        "This request involves a high-risk domain (self-harm, medical, "
                        "legal, or consequential decisions). Please consult a qualified "
                        "professional or contact emergency services if needed."
                    ),
                    confidence=0.82,
                )

        # --- Medium-risk check (§10.2: respond with safeguards) ---
        for pattern in _MEDIUM:
            if pattern.search(text):
                return MoralResult(
                    risk_level=RiskLevel.MEDIUM,
                    decision=Decision.COMPLY_WITH_SAFEGUARDS,
                    rationale=(
                        "This request touches a sensitive topic. "
                        "Responding with appropriate care and disclaimers."
                    ),
                    confidence=0.72,
                )

        # --- Default: low risk (§10.1) ---
        return MoralResult(
            risk_level=RiskLevel.LOW,
            decision=Decision.COMPLY,
            rationale="No significant risk detected.",
            confidence=0.90,
        )
