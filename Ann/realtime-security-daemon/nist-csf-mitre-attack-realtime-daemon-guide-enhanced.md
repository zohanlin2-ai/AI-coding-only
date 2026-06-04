# Python Real-Time Security Detection Framework

## Development Guide: Real-Time Daemon Edition

> This enhanced guide extends the real-time daemon design with production-oriented improvements: event persistence, alert deduplication, rule schema versioning, Windows-compatible lifecycle controls, backpressure handling, safer LLM enrichment, and clearer time-window semantics.

---

## 1. Purpose

This document describes how to build a Python-based real-time security detection daemon that uses the NIST Cybersecurity Framework (NIST CSF) for capability coverage and MITRE ATT&CK for concrete detection logic.

The main design principles are:

- Use NIST CSF to define what cybersecurity capabilities the system should cover.
- Use MITRE ATT&CK to define what adversary techniques the system should detect.
- Use Python to connect both frameworks into a continuously running daemon with live event collection, real-time rule evaluation, immediate alerting, and periodic reporting.
- Keep detection logic externalized in YAML so rules can be reviewed, versioned, tested, and updated without changing Python code.
- Keep the daemon resilient: collectors should fail independently, queues should be bounded, alerts should be deduplicated, and expensive enrichment should never block detection.

---

## 2. Recommended MVP Scope

For an initial MVP, cover these NIST CSF functions:

- Identify
- Protect
- Detect
- Respond

NIST CSF 2.0 also includes:

- Govern
- Recover

Even if the MVP does not fully implement Govern and Recover, the data model should reserve fields for them so the system can expand later without redesigning the core structure.

Recommended MVP capabilities:

- Live process activity collection.
- Live filesystem activity collection.
- YAML-based detection rules.
- Real-time event queue.
- Sliding-window detection for count-based behaviors.
- Immediate alert generation.
- JSON Lines alert persistence.
- Basic alert deduplication and throttling.
- Scheduled Markdown and JSON reports.
- CSF and MITRE ATT&CK coverage reporting.

---

## 3. Conceptual Architecture

The architecture is event-driven and designed for a continuously running daemon.

```text
Event Collectors
  -> Parsers / Normalizers
  -> Thread-Safe Event Queue
  -> Detection Engine
  -> Time Window Manager
  -> Alert Deduplicator
  -> Alert Handler
  -> Persistence Layer
  -> Periodic Reporter
```

The queue decouples collection from detection. This prevents slow rule evaluation, alert delivery, or enrichment from blocking event ingestion.

### 3.1 Core Components

| Component | Role |
|---|---|
| `collectors/` | Long-running event source workers. |
| `parsers/` | Normalize raw events into a common event schema. |
| `queue_manager.py` | Bounded thread-safe queue with overflow tracking. |
| `engine.py` | Consumes normalized events and evaluates enabled rules. |
| `window_manager.py` | Maintains sliding windows for count-based rules. |
| `deduplicator.py` | Suppresses repeated alerts within a configurable cooldown. |
| `alert_handler.py` | Emits alerts to configured channels without blocking the engine. |
| `storage.py` | Persists alerts, health metrics, and optionally normalized events. |
| `daemon.py` | Manages lifecycle, shutdown, reload, watchdog, and service behavior. |
| `reports/` | Produces scheduled coverage, alert, and health reports. |
| `response/` | Maps alerts to recommended playbook actions. |

---

## 4. NIST CSF Usage

NIST CSF is used as a coverage and planning framework. It should not be treated as low-level detection logic.

Use it to:

- Verify cybersecurity capability coverage.
- Map modules and rules to business-friendly security functions.
- Produce coverage reports.
- Identify missing security functions.
- Communicate system scope to stakeholders.

### 4.1 Capability Mapping

| NIST CSF Function | Example Python Capability | Daemon Component |
|---|---|---|
| Govern | Policy mapping, ownership, risk scoring, coverage reporting | `reports/coverage_report.py` |
| Identify | Asset inventory, process baseline, network connection map | `collectors/process_collector.py` |
| Protect | Baseline checks, allowlists, risky configuration detection | `config_checker.py` |
| Detect | Real-time rule engine, MITRE ATT&CK detections | `engine.py` |
| Respond | Immediate alerts, recommended actions, incident summaries | `alert_handler.py`, `response/` |
| Recover | Recovery checklist, backup validation summary | `reports/recovery_report.py` |

Example capability mapping:

```yaml
module: process_collector
description: Tracks process activity and emits normalized process creation events.
csf:
  function: Identify
  category: ID.AM
```

---

## 5. MITRE ATT&CK Usage

MITRE ATT&CK is used for detection rule metadata and adversary behavior mapping.

Each detection rule should include:

- ATT&CK tactic.
- Technique ID.
- Technique name.
- Event source.
- Detection logic.
- Evidence fields.
- Severity.
- Response recommendations.

Example techniques:

- `T1059`: Command and Scripting Interpreter.
- `T1486`: Data Encrypted for Impact.

MITRE ATT&CK IDs should describe what the rule is detecting. They should not replace clear rule logic.

---

## 6. Rule Format

Every rule should include a schema version. This makes future rule migrations possible.

### 6.1 Example Rule: T1059 Suspicious Command Interpreter

```yaml
schema_version: 1
id: R-001
name: Suspicious command interpreter usage
description: Detects suspicious use of shell or scripting interpreters.
enabled: true
severity: high

csf:
  function: Detect
  category: DE.CM

mitre:
  tactic: Execution
  technique_id: T1059
  technique_name: Command and Scripting Interpreter

event:
  source: process_creation

logic:
  all:
    - field: process_name
      operator: in
      value:
        - cmd.exe
        - powershell.exe
        - pwsh.exe
        - bash
        - sh
    - field: command_line
      operator: contains_any
      value:
        - "-enc"
        - "IEX"
        - "curl"
        - "wget"
        - "Invoke-WebRequest"

dedup:
  cooldown_seconds: 300
  group_by:
    - rule_id
    - host
    - user
    - process_name

response:
  playbook: suspicious_shell_usage
  recommended_actions:
    - Review command line and parent process.
    - Check user account context.
    - Isolate host if execution appears malicious.
```

### 6.2 Example Rule: T1486 Ransomware-Like Encryption

This rule uses a sliding time window. The `group_by` fields define the scope of counting.

```yaml
schema_version: 1
id: R-002
name: Possible ransomware file encryption activity
description: Detects rapid file modification and suspicious extension changes.
enabled: true
severity: critical

csf:
  function: Detect
  category: DE.CM

mitre:
  tactic: Impact
  technique_id: T1486
  technique_name: Data Encrypted for Impact

event:
  source: file_activity

window:
  duration_seconds: 300
  group_by:
    - host
    - user
  counters:
    - name: file_operation_count_5m
      event_types:
        - created
        - modified
        - renamed
    - name: extension_change_count_5m
      event_types:
        - renamed

logic:
  all:
    - field: file_operation_count_5m
      operator: greater_than
      value: 500
    - field: extension_change_count_5m
      operator: greater_than
      value: 100
    - field: new_extension
      operator: matches_any
      value:
        - ".locked"
        - ".encrypted"
        - ".crypt"

dedup:
  cooldown_seconds: 600
  group_by:
    - rule_id
    - host
    - user

response:
  playbook: ransomware_containment
  recommended_actions:
    - Isolate affected endpoint immediately.
    - Disable suspected user account.
    - Preserve process, file, and network evidence.
    - Validate backup availability.
```

---

## 7. Python Data Model

Use dataclasses for a lightweight MVP or Pydantic for stricter validation.

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class CsfMapping:
    function: str
    category: str | None = None


@dataclass
class MitreMapping:
    tactic: str
    technique_id: str
    technique_name: str


@dataclass
class DetectionRule:
    schema_version: int
    id: str
    name: str
    description: str
    enabled: bool
    severity: str
    csf: CsfMapping
    mitre: MitreMapping
    event_source: str
    logic: dict[str, Any]
    response: dict[str, Any]
    window: dict[str, Any] | None = None
    dedup: dict[str, Any] | None = None


@dataclass
class NormalizedEvent:
    event_source: str
    timestamp: datetime
    host: str
    data: dict[str, Any]


@dataclass
class Alert:
    rule_id: str
    title: str
    severity: str
    csf: CsfMapping
    mitre: MitreMapping
    evidence: dict[str, Any]
    recommended_actions: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    host: str | None = None
    dedup_key: str | None = None
    correlation_id: str | None = None
    llm_analysis: dict[str, Any] | None = None
```

Use timezone-aware UTC timestamps for all internal processing.

---

## 8. Rule Engine Behavior

At startup, the engine should:

1. Load configuration.
2. Load and validate all rules.
3. Initialize the bounded event queue.
4. Initialize the window manager.
5. Initialize storage.
6. Start configured collector workers.
7. Start the detection loop.
8. Start scheduled reporting and health monitoring.

For each event, the engine should:

1. Receive one normalized event from the queue.
2. Persist the event if event persistence is enabled.
3. Select enabled rules matching the event source.
4. Update relevant sliding windows.
5. Inject window counters into the event.
6. Evaluate rule logic.
7. Generate an alert for matching rules.
8. Run deduplication and cooldown checks.
9. Persist the alert.
10. Send the alert to configured output channels.
11. Submit expensive enrichment tasks to a background worker.

The detection loop should not perform network calls, LLM calls, long file writes, or slow webhook requests directly.

---

## 9. Event Queue and Backpressure

The queue must be bounded. An unbounded queue can consume all memory during event spikes.

Required queue metrics:

- Current queue depth.
- Maximum queue size.
- Events accepted.
- Events dropped.
- Overflow rate.
- Average event processing latency.

Recommended behavior:

- Use non-blocking `put`.
- Drop low-priority noisy events first if possible.
- Never drop high-value alert records after detection.
- Emit health metrics when overflow occurs.
- Include overflow indicators in periodic reports.

Example config:

```yaml
queue:
  max_size: 10000
  overflow_policy: drop_newest
  warn_at_percent: 80
```

---

## 10. Sliding Window Manager

The window manager is required for count-based rules.

It should support:

- Per-rule windows.
- Per-counter windows.
- `group_by` keys such as host, user, process, directory, or source IP.
- Periodic cleanup.
- Deterministic testing with injected timestamps.

Example window key:

```text
R-002:file_operation_count_5m:host=WIN-ENDPOINT-01:user=alice
```

Time-window bugs are difficult to diagnose in production, so unit tests should cover:

- Window boundary behavior.
- Old event cleanup.
- Multiple hosts and users.
- Out-of-order timestamps.
- High-volume event bursts.

---

## 11. Alert Deduplication and Suppression

Real-time detection can generate repeated alerts for the same underlying activity. Add a deduplication layer before alert delivery.

Deduplication should support:

- Per-rule cooldown.
- Grouping by selected fields.
- Alert count aggregation.
- First seen and last seen timestamps.
- Suppression reason.

Example dedup key:

```text
R-001|host=WIN-ENDPOINT-01|user=alice|process_name=powershell.exe
```

Recommended behavior:

- Persist the first alert.
- Suppress repeated alerts within the cooldown window.
- Increment a suppressed count.
- Include suppressed counts in summary reports.

---

## 12. Persistence Layer

The daemon needs a local persistence layer for investigation, reporting, and recovery after restart.

MVP options:

- JSON Lines for simple alert logs.
- SQLite for searchable local storage.

Recommended MVP:

- Write alerts to JSON Lines immediately.
- Store daemon health metrics separately.
- Optionally store normalized events in SQLite with retention.

Example files:

```text
logs/
  alerts.jsonl
  daemon-health.jsonl
  crash.log
data/
  security_detection.db
```

Retention should be configurable:

```yaml
retention:
  alerts_days: 30
  events_days: 7
  health_days: 14
```

---

## 13. Collectors

### 13.1 Collector Interface

```python
class BaseCollector(threading.Thread):
    def __init__(self, event_queue, config: dict): ...
    def run(self) -> None: ...
    def stop(self) -> None: ...
    def is_healthy(self) -> bool: ...
```

### 13.2 Recommended Collectors

| Collector | Source | Notes |
|---|---|---|
| `ProcessCollector` | `psutil` polling | Easy MVP, but may miss short-lived processes. |
| `FileCollector` | `watchdog` | Good for watched directories and ransomware-like behavior. |
| `NetworkCollector` | `psutil` polling | Useful for outbound connection monitoring. |
| `WindowsEventCollector` | Windows Event Log | Better source for process creation on Windows. |
| `SysmonCollector` | Sysmon event logs | Recommended for richer endpoint telemetry. |

For Windows process creation, prefer Sysmon Event ID 1 or Windows Security Event ID 4688 when available. `psutil` polling is acceptable for MVP but should be documented as best-effort telemetry.

---

## 14. Daemon Lifecycle

The daemon should support:

- Start.
- Stop.
- Graceful shutdown.
- Rule reload.
- Health check.
- Crash logging.
- Collector watchdog.
- Service installation.

Unix-like systems can use signals such as `SIGTERM`, `SIGINT`, and `SIGHUP`.

Windows requires alternatives for reload and service control:

- CLI command: `security-daemon reload`.
- Local admin endpoint: `POST /admin/reload`.
- Config file watcher.
- Windows Service control through `pywin32`.

Do not rely exclusively on `SIGHUP` if Windows is a supported platform.

---

## 15. Alert Handler

Alerts must be emitted immediately and safely.

Recommended channels:

| Channel | Use Case |
|---|---|
| Terminal | Development and manual testing. |
| JSON Lines file | Persistent alert record and SIEM ingestion. |
| Webhook | Ticketing, chat, SOAR, or internal API integration. |
| OS notification | Local endpoint notification for critical alerts. |

All non-terminal channels should use a background worker or async queue so the detection loop is not blocked by slow I/O.

---

## 16. LLM-Assisted Analysis

LLM analysis should be treated as alert enrichment, not primary detection.

Recommended behavior:

- Trigger only after a high or critical rule fires.
- Send enrichment work to a background worker.
- Cache results by file hash, command hash, or script hash.
- Rate-limit API calls.
- Store results under `alert.llm_analysis`.
- Never block the detection loop.
- Never use LLM output as the only reason for automatic containment.

Example output shape:

```json
{
  "risk_score": 85,
  "verdict": "suspicious",
  "suspicious_behaviors": [
    "Encoded command execution",
    "Network download followed by execution"
  ],
  "analyst_summary": "The command resembles common script-based execution behavior."
}
```

---

## 17. Recommended Project Structure

```text
security_detection_framework/
  pyproject.toml
  README.md
  config/
    daemon.yml
    allowlists.yml
    retention.yml
  rules/
    t1059_suspicious_command_interpreter.yml
    t1486_ransomware_file_encryption.yml
  logs/
    alerts.jsonl
    daemon-health.jsonl
    crash.log
  data/
    security_detection.db
  src/
    security_detection/
      __init__.py
      models.py
      rule_loader.py
      operators.py
      engine.py
      daemon.py
      queue_manager.py
      window_manager.py
      deduplicator.py
      storage.py
      alert_handler.py
      collectors/
        __init__.py
        base_collector.py
        process_collector.py
        file_collector.py
        network_collector.py
        windows_event_collector.py
        sysmon_collector.py
      parsers/
        __init__.py
        process_parser.py
        file_parser.py
        network_parser.py
        windows_event_parser.py
      reports/
        __init__.py
        markdown_report.py
        json_report.py
        coverage_report.py
        health_report.py
      response/
        __init__.py
        playbooks.py
      enrichment/
        __init__.py
        llm_analyzer.py
        cache.py
  tests/
    test_rule_loader.py
    test_engine.py
    test_window_manager.py
    test_deduplicator.py
    test_queue_manager.py
    test_coverage_report.py
```

---

## 18. MVP Implementation Plan

### Phase 1: Framework Skeleton

- Create Python package structure.
- Define dataclasses or Pydantic models.
- Create YAML rule format with `schema_version`.
- Implement rule loading and validation.

### Phase 2: Detection Engine

- Implement basic operators:
  - `equals`
  - `in`
  - `contains`
  - `contains_any`
  - `greater_than`
  - `less_than`
  - `matches_any`
- Support `all` and `any` logic groups.
- Generate structured alerts.

### Phase 3: Real-Time Infrastructure

- Implement `BaseCollector`.
- Implement `ProcessCollector`.
- Implement `FileCollector`.
- Implement `QueueManager`.
- Implement `WindowManager`.
- Add unit tests for time-window behavior.

### Phase 4: Persistence and Deduplication

- Write alerts to JSON Lines.
- Add daemon health log.
- Implement deduplication cooldown.
- Add suppression counters.

### Phase 5: Daemon Lifecycle

- Implement start, stop, and graceful shutdown.
- Add config loading.
- Add rule reload.
- Add collector watchdog.
- Add crash logging.
- Add Windows-compatible reload approach if Windows is supported.

### Phase 6: Example Rules and Alert Output

- Wire `T1059` rule to process events.
- Wire `T1486` rule to file activity events.
- Emit terminal alerts.
- Persist JSONL alerts.
- Test end-to-end flow.

### Phase 7: Reporting

- Generate scheduled Markdown alert report.
- Generate JSON alert export.
- Generate CSF coverage report.
- Generate MITRE ATT&CK coverage report.
- Generate daemon health report.

### Phase 8: Response Support

- Attach playbooks to rules.
- Include recommended response actions in each alert.
- Add incident summary output.

### Phase 9: LLM Enrichment

- Add optional enrichment worker.
- Cache results by hash.
- Rate-limit API calls.
- Attach enrichment output to alerts.

---

## 19. Coverage Report Requirements

The system should answer:

- Which NIST CSF functions are covered?
- Which NIST CSF functions are missing?
- Which MITRE ATT&CK techniques are covered by enabled rules?
- Which rules are enabled or disabled?
- Which detections generated alerts in the last 24 hours?
- Which collectors are healthy?
- What is the current queue depth?
- Has event overflow occurred?
- How many alerts were suppressed by deduplication?

Example report:

```markdown
# Security Detection Coverage Report

## NIST CSF Coverage

| Function | Covered | Rules / Modules |
|---|---:|---|
| Govern | Partial | coverage_report |
| Identify | Yes | process_collector, file_collector |
| Protect | Partial | allowlists |
| Detect | Yes | R-001, R-002 |
| Respond | Yes | alert_handler, response_playbooks |
| Recover | Partial | recovery_report |

## MITRE ATT&CK Coverage

| Technique ID | Technique Name | Rules |
|---|---|---|
| T1059 | Command and Scripting Interpreter | R-001 |
| T1486 | Data Encrypted for Impact | R-002 |

## Daemon Health

| Metric | Value |
|---|---:|
| Queue depth | 12 |
| Queue overflow count | 0 |
| Alerts last hour | 4 |
| Suppressed alerts last hour | 23 |
```

---

## 20. Security and Operational Considerations

- Avoid automatic containment in the first version.
- Treat response actions as recommendations until confidence is proven.
- Store raw evidence for analyst review.
- Protect rule files from unauthorized modification.
- Validate rule files before loading them.
- Log daemon health separately from security alerts.
- Run with the minimum privilege required.
- Avoid storing secrets in YAML config files.
- Redact sensitive values from reports when necessary.
- Use allowlists and maintenance windows to reduce false positives.
- Monitor queue overflow because dropped events reduce detection reliability.

---

## 21. Definition of Done for MVP

The MVP is complete when it can:

- Load at least two detection rules from YAML.
- Validate rule schema version and required fields.
- Start process and file collectors.
- Run continuously for at least one hour without crashing.
- Detect suspicious command interpreter usage mapped to `T1059`.
- Detect ransomware-like file behavior mapped to `T1486`.
- Use sliding windows with explicit `group_by` keys.
- Generate alerts immediately.
- Deduplicate repeated alerts.
- Persist alerts to JSON Lines.
- Record daemon health metrics.
- Shut down gracefully.
- Reload rules without restarting the whole daemon.
- Produce CSF coverage report.
- Produce MITRE ATT&CK coverage report.
- Include response recommendations for each alert.

