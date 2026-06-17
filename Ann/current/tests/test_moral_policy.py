"""
Tests for moral_policy.load_policy — spec §8.3 minimum validation and §8.4/§19.1
behaviour-relevant config layer. Bad configuration must never widen safety.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from moral_policy import MoralPolicy, load_policy


# --- defaults --------------------------------------------------------------

def test_empty_config_yields_safe_defaults() -> None:
    p = load_policy({})
    assert p.enabled is True
    assert p.classifier == "hybrid"
    assert p.risk_tolerance == "medium"
    assert p.logging.enabled is False            # §8.4 logging defaults off/redacted
    assert p.emergency.enabled is True           # §8.3 emergency must be present
    assert p.allow_automatic_moral_updates is False


def test_missing_moral_section() -> None:
    p = load_policy({"llm": {"model": "x"}})
    assert isinstance(p, MoralPolicy)
    assert p.emergency.local_only_mode is True
    assert p.emergency.allow_external_contact is False   # §19.1 default false


# --- §8.3 invalid values coerced to safe defaults --------------------------

def test_invalid_classifier_coerced() -> None:
    p = load_policy({"moral": {"classifier": "psychic"}})
    assert p.classifier == "hybrid"


def test_invalid_risk_tolerance_coerced() -> None:
    p = load_policy({"moral": {"risk_tolerance": "reckless"}})
    assert p.risk_tolerance == "medium"


def test_invalid_escalation_coerced() -> None:
    p = load_policy({"moral": {"preferred_escalation": "call_the_president"}})
    assert p.preferred_escalation == "ask_me"


# --- §20 invariant: moral updates are never automatic ----------------------

def test_auto_moral_update_forced_false() -> None:
    p = load_policy({"update": {"allow_automatic_moral_updates": True}})
    assert p.allow_automatic_moral_updates is False


# --- valid config round-trips ----------------------------------------------

def test_valid_config_round_trips() -> None:
    cfg = {
        "moral": {
            "enabled": True,
            "classifier": "rules",
            "risk_tolerance": "low",
            "preferred_escalation": "recommend_professional",
            "sensitive_topics": ["finances"],
            "high_risk_domains": ["medical", "legal"],
            "logging": {"enabled": True, "audit_medium_and_above": True},
            "emergency": {
                "enabled": True,
                "local_only_mode": True,
                "allow_external_contact": False,
                "emergency_services_label": "112",
                "crisis_resources": [{"label": "Hotline", "contact": "1995"}],
            },
        }
    }
    p = load_policy(cfg)
    assert p.classifier == "rules"
    assert p.risk_tolerance == "low"
    assert p.high_risk_domains == ["medical", "legal"]
    assert p.logging.enabled is True
    assert p.emergency.emergency_services_label == "112"
    assert p.emergency.crisis_resources[0]["contact"] == "1995"
