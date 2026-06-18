"""
Moral governance metrics — spec §11.5 (classifier error monitoring) and §24
(governance review).

Consumes the redacted audit log written by the moral evaluator
(`logs/moral_audit.jsonl`) plus an optional user-correction log
(`logs/moral_corrections.jsonl`) and produces a decision-distribution report.

This makes the audit trail actionable: it surfaces refusal / escalation rates
and lets the user flag a decision as a false positive (over-refusal or
over-escalation), the one signal the classifier cannot self-measure.

No personal data is read or stored beyond what the audit log already holds
(which is redacted at write time).
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

AUDIT_FILENAME = "moral_audit.jsonl"
CORRECTIONS_FILENAME = "moral_corrections.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file, skipping blank and malformed lines. Never raises."""
    records: list[dict] = []
    if not path.exists():
        return records
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue  # skip a corrupt line rather than failing the report
                if isinstance(obj, dict):
                    records.append(obj)
    except OSError:
        return records
    return records


def load_audit_records(logs_dir) -> list[dict]:
    return _read_jsonl(Path(logs_dir) / AUDIT_FILENAME)


def load_corrections(logs_dir) -> list[dict]:
    return _read_jsonl(Path(logs_dir) / CORRECTIONS_FILENAME)


def summarize(records: list[dict], corrections: list[dict] | None = None) -> dict:
    """Aggregate audit records into decision/risk/escalation distributions and rates."""
    corrections = corrections or []
    total = len(records)
    by_decision = Counter(r.get("decision", "unknown") for r in records)
    by_risk = Counter(r.get("risk_level", "unknown") for r in records)
    by_escalation = Counter(r.get("local_escalation_level", "unknown") for r in records)

    def rate(n: int) -> float:
        return (n / total) if total else 0.0

    return {
        "total": total,
        "by_decision": dict(by_decision),
        "by_risk": dict(by_risk),
        "by_escalation": dict(by_escalation),
        "refusal_rate": rate(by_decision.get("refuse", 0)),
        "escalation_rate": rate(by_decision.get("escalate_or_pause", 0)),
        "safeguard_rate": rate(by_decision.get("comply_with_safeguards", 0)),
        "flagged_false_positives": len(corrections),
        "flagged_rate": rate(len(corrections)),
    }


def format_report(summary: dict) -> str:
    """Render a summary dict as a human-readable report."""
    if summary["total"] == 0:
        return (
            "📋 Moral governance: no audit records yet.\n"
            "(Audit logging is active only when moral.logging.enabled is true in config.yml.)"
        )
    dec = summary["by_decision"]
    lines = [
        "📋 Moral Governance Report (spec §11.5)",
        f"  • Audited decisions (medium-risk and above): {summary['total']}",
        f"  • Refusals: {dec.get('refuse', 0)} ({summary['refusal_rate'] * 100:.0f}%)",
        f"  • Escalations: {dec.get('escalate_or_pause', 0)} ({summary['escalation_rate'] * 100:.0f}%)",
        f"  • Comply-with-safeguards: {dec.get('comply_with_safeguards', 0)} "
        f"({summary['safeguard_rate'] * 100:.0f}%)",
        "  • By escalation level: "
        + (", ".join(f"{k}={v}" for k, v in sorted(summary["by_escalation"].items())) or "—"),
        f"  • User-flagged false positives: {summary['flagged_false_positives']} "
        f"({summary['flagged_rate'] * 100:.0f}%)",
    ]
    if summary["flagged_rate"] > 0.2:
        lines.append("  ⚠️  High flagged-false-positive rate — review over-refusal / over-escalation.")
    return "\n".join(lines)


def record_correction(logs_dir, request_id: str, note: str = "") -> dict:
    """Append a user false-positive flag to the corrections log. Returns the record."""
    logs_path = Path(logs_dir)
    logs_path.mkdir(exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "note": note,
        "type": "false_positive",
    }
    with open(logs_path / CORRECTIONS_FILENAME, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def latest_request_id(records: list[dict]) -> str | None:
    """Return the request_id of the most recent audit record, or None."""
    for record in reversed(records):
        rid = record.get("request_id")
        if rid:
            return rid
    return None
