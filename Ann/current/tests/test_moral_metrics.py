"""
Tests for moral_metrics — spec §11.5 governance reporting over the audit log.

Covers boundary conditions (empty, missing fields, malformed lines) and the
correction-flagging round trip, plus the /moral slash command wiring.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from moral_metrics import (
    AUDIT_FILENAME,
    format_report,
    latest_request_id,
    load_audit_records,
    load_corrections,
    record_correction,
    summarize,
)
from slash_commands import handle_slash_command


def _write_audit(logs_dir: Path, records: list[dict]) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    with open(logs_dir / AUDIT_FILENAME, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


# --- boundary: empty / missing file ----------------------------------------

def test_load_audit_missing_dir_returns_empty(tmp_path):
    assert load_audit_records(tmp_path / "logs") == []


def test_summarize_empty_is_zero():
    s = summarize([])
    assert s["total"] == 0
    assert s["refusal_rate"] == 0.0
    assert "no audit records" in format_report(s).lower()


# --- boundary: malformed and null fields -----------------------------------

def test_malformed_lines_skipped(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    with open(logs / AUDIT_FILENAME, "w", encoding="utf-8") as f:
        f.write('{"decision": "refuse", "risk_level": "prohibited"}\n')
        f.write("not json at all\n")
        f.write("\n")
        f.write('{"decision": "comply_with_safeguards"}\n')
    records = load_audit_records(logs)
    assert len(records) == 2  # the two valid lines only


def test_summarize_tolerates_missing_fields():
    records = [{"decision": "refuse"}, {}, {"risk_level": "medium"}]
    s = summarize(records)
    assert s["total"] == 3
    assert s["by_decision"].get("unknown") == 2  # the two without a decision
    assert s["by_risk"].get("unknown") == 2


# --- distribution and rates ------------------------------------------------

def test_rates_and_distribution():
    records = [
        {"decision": "refuse", "risk_level": "prohibited", "local_escalation_level": "E5"},
        {"decision": "escalate_or_pause", "risk_level": "high", "local_escalation_level": "E1"},
        {"decision": "comply_with_safeguards", "risk_level": "medium",
         "local_escalation_level": "E2"},
        {"decision": "comply_with_safeguards", "risk_level": "medium",
         "local_escalation_level": "E2"},
    ]
    s = summarize(records)
    assert s["total"] == 4
    assert s["refusal_rate"] == 0.25
    assert s["escalation_rate"] == 0.25
    assert s["safeguard_rate"] == 0.5
    assert s["by_escalation"]["E2"] == 2
    report = format_report(s)
    assert "Refusals: 1" in report
    assert "E2=2" in report


# --- corrections round trip ------------------------------------------------

def test_record_and_load_correction(tmp_path):
    logs = tmp_path / "logs"
    rec = record_correction(logs, "abc123", "benign academic question")
    assert rec["request_id"] == "abc123"
    assert rec["type"] == "false_positive"
    loaded = load_corrections(logs)
    assert len(loaded) == 1
    assert loaded[0]["note"] == "benign academic question"


def test_flagged_rate_in_summary():
    records = [{"decision": "escalate_or_pause"}, {"decision": "refuse"}]
    s = summarize(records, corrections=[{"request_id": "x"}])
    assert s["flagged_false_positives"] == 1
    assert s["flagged_rate"] == 0.5


def test_latest_request_id():
    assert latest_request_id([]) is None
    assert latest_request_id([{"request_id": "a"}, {"request_id": "b"}]) == "b"
    assert latest_request_id([{"request_id": "a"}, {"foo": "bar"}]) == "a"


# --- slash command wiring --------------------------------------------------

def test_slash_moral_stats(tmp_path):
    _write_audit(tmp_path / "logs", [{"decision": "refuse", "risk_level": "prohibited"}])
    result = handle_slash_command("/moral stats", controller=None, base_dir=tmp_path)
    assert result.handled is True
    assert "Refusals: 1" in result.reply


def test_slash_moral_default_is_stats(tmp_path):
    result = handle_slash_command("/moral", controller=None, base_dir=tmp_path)
    assert result.handled is True
    assert "no audit records" in result.reply.lower()


def test_slash_moral_flag(tmp_path):
    _write_audit(tmp_path / "logs", [{"request_id": "req-1", "decision": "escalate_or_pause"}])
    result = handle_slash_command("/moral flag too cautious", controller=None, base_dir=tmp_path)
    assert result.handled is True
    assert "req-1" in result.reply
    assert load_corrections(tmp_path / "logs")[0]["note"] == "too cautious"


def test_slash_moral_flag_nothing_to_flag(tmp_path):
    result = handle_slash_command("/moral flag", controller=None, base_dir=tmp_path)
    assert result.handled is True
    assert "no audited decision" in result.reply.lower()
