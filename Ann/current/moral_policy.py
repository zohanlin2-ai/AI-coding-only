"""
Moral Policy — typed configuration layer for the moral module.

Implements the behaviour-relevant subset of moral_module_spec.md §8.4
(MoralPolicyConfig) and §19.1 (EmergencyBehaviorConfig), built from the
``moral:`` section of config.yml.

The spec (moral_module_spec.md) must NOT be modified. This file implements its
configuration contract; the spec defines it.

§8.3 minimum validation rules enforced here:
  - allowAutomaticMoralUpdates must be false (cross-checked against config.update)
  - external notifications default to false
  - logging defaults to redacted / disabled
  - emergency behaviour must be present
A failing rule never *widens* safety: it logs and falls back to the safe default.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_VALID_TOLERANCE = {"low", "medium", "high"}
_VALID_ESCALATION = {"ask_me", "pause", "recommend_professional", "require_second_human"}
_VALID_CLASSIFIER = {"hybrid", "rules"}


@dataclass
class EmergencyConfig:
    """spec §19.1 EmergencyBehaviorConfig (behaviour-relevant subset)."""

    enabled: bool = True
    local_only_mode: bool = True
    allow_external_contact: bool = False
    external_contact_requires_consent: bool = True
    emergency_services_label: str = "your local emergency number"
    crisis_resources: list[dict] = field(default_factory=list)
    imminent_risk_triggers: list[str] = field(default_factory=list)


@dataclass
class LoggingConfig:
    """spec §8.4 logging block (behaviour-relevant subset)."""

    enabled: bool = False
    audit_medium_and_above: bool = True


@dataclass
class MoralPolicy:
    """spec §8.4 MoralPolicyConfig (behaviour-relevant subset)."""

    enabled: bool = True
    classifier: str = "hybrid"
    risk_tolerance: str = "medium"
    preferred_escalation: str = "ask_me"
    sensitive_topics: list[str] = field(default_factory=list)
    high_risk_domains: list[str] = field(
        default_factory=lambda: ["medical", "legal", "financial", "employment", "housing"]
    )
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    emergency: EmergencyConfig = field(default_factory=EmergencyConfig)
    # §8.4 updates invariant — cross-checked, never auto-true for the moral module.
    allow_automatic_moral_updates: bool = False


def _coerce_choice(value, valid: set[str], default: str, name: str) -> str:
    if value in valid:
        return value
    logger.warning("Invalid moral.%s=%r; falling back to safe default %r", name, value, default)
    return default


def load_policy(config: dict) -> MoralPolicy:
    """
    Build a MoralPolicy from the parsed config.yml dict.

    Missing ``moral:`` section yields all safe defaults. Invalid values are
    logged and replaced by the safe default — bad configuration never widens
    safety (spec §8.3).
    """
    moral_cfg = (config or {}).get("moral") or {}

    emg_cfg = moral_cfg.get("emergency") or {}
    emergency = EmergencyConfig(
        enabled=bool(emg_cfg.get("enabled", True)),
        local_only_mode=bool(emg_cfg.get("local_only_mode", True)),
        allow_external_contact=bool(emg_cfg.get("allow_external_contact", False)),
        external_contact_requires_consent=bool(
            emg_cfg.get("external_contact_requires_consent", True)
        ),
        emergency_services_label=str(
            emg_cfg.get("emergency_services_label", "your local emergency number")
        ),
        crisis_resources=list(emg_cfg.get("crisis_resources") or []),
        imminent_risk_triggers=list(emg_cfg.get("imminent_risk_triggers") or []),
    )

    log_cfg = moral_cfg.get("logging") or {}
    logging_conf = LoggingConfig(
        enabled=bool(log_cfg.get("enabled", False)),
        audit_medium_and_above=bool(log_cfg.get("audit_medium_and_above", True)),
    )

    # §8.3: cross-check the moral-update invariant against config.update.
    update_cfg = (config or {}).get("update") or {}
    allow_auto_moral = bool(update_cfg.get("allow_automatic_moral_updates", False))
    if allow_auto_moral:
        logger.error(
            "config.update.allow_automatic_moral_updates is true — violates spec §20; "
            "forcing false."
        )
        allow_auto_moral = False

    policy = MoralPolicy(
        enabled=bool(moral_cfg.get("enabled", True)),
        classifier=_coerce_choice(
            moral_cfg.get("classifier", "hybrid"), _VALID_CLASSIFIER, "hybrid", "classifier"
        ),
        risk_tolerance=_coerce_choice(
            moral_cfg.get("risk_tolerance", "medium"), _VALID_TOLERANCE, "medium", "risk_tolerance"
        ),
        preferred_escalation=_coerce_choice(
            moral_cfg.get("preferred_escalation", "ask_me"),
            _VALID_ESCALATION,
            "ask_me",
            "preferred_escalation",
        ),
        sensitive_topics=list(moral_cfg.get("sensitive_topics") or []),
        high_risk_domains=list(
            moral_cfg.get("high_risk_domains")
            or ["medical", "legal", "financial", "employment", "housing"]
        ),
        logging=logging_conf,
        emergency=emergency,
        allow_automatic_moral_updates=allow_auto_moral,
    )
    return policy
