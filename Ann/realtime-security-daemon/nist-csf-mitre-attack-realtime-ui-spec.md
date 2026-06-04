# UI Specification for the Real-Time Security Detection Daemon

## Purpose

This document defines a simple UI for the Python real-time security detection daemon described in `nist-csf-mitre-attack-realtime-daemon-guide.md`.

The UI should help an analyst or developer quickly answer four questions:

1. Is the daemon healthy?
2. What alerts are happening now?
3. Which rules are enabled and working?
4. What NIST CSF and MITRE ATT&CK coverage do we have?

The UI should stay compact, operational, and easy to understand. It is not a marketing page and should not require deep cybersecurity knowledge to navigate.

---

## Design Principles

- Show current status first.
- Keep navigation small.
- Prefer tables, filters, and detail drawers over complex visualizations.
- Make severity, host, rule, MITRE technique, and NIST CSF function easy to scan.
- Keep actions manual in the first version.
- Do not hide raw evidence from analysts.
- Use the daemon's existing data model: alerts, rules, collectors, queue metrics, health metrics, CSF mappings, and MITRE mappings.

---

## Recommended UI Navigation

Use four primary tabs:

```text
Dashboard | Alerts | Rules | Coverage
```

Optional later tabs:

```text
Events | Settings | Reports
```

For MVP, implement only:

- Dashboard
- Alerts
- Rules
- Coverage

---

## 1. Dashboard

### Goal

Show whether the real-time daemon is running correctly.

### Data Sources

From the daemon guide:

- `daemon.py`
- `queue_manager.py`
- `collectors/`
- `alert_handler.py`
- `storage.py`
- `daemon-health.jsonl`

### Main Cards

Show compact status cards at the top:

| Card | Example Value |
|---|---|
| Daemon Status | Running |
| Queue Depth | 12 / 10,000 |
| Queue Overflow | 0 |
| Events / Minute | 320 |
| Alerts / Hour | 4 |
| Critical Alerts | 1 |

### Collector Health Table

| Collector | Status | Events Last 5m | Last Event | Errors |
|---|---|---:|---|---:|
| ProcessCollector | Healthy | 840 | 10:42:12 | 0 |
| FileCollector | Healthy | 1,204 | 10:42:10 | 0 |
| NetworkCollector | Stopped | 0 | - | 1 |

### Recent Alerts

Show the latest 5 to 10 alerts.

Columns:

- Time
- Severity
- Rule
- Host
- User
- MITRE Technique

Clicking an alert opens the same detail drawer used in the Alerts page.

### Useful States

- Running
- Degraded
- Stopped
- Queue overflow
- Collector failed
- Rule reload failed

---

## 2. Alerts

### Goal

Let analysts review, filter, and investigate generated alerts.

### Data Sources

From the daemon guide:

- `alerts.jsonl`
- `storage.py`
- `Alert` dataclass
- `deduplicator.py`
- `response/playbooks.py`

### Alert List

Use a dense table.

Columns:

- Time
- Severity
- Status
- Rule ID
- Rule Name
- Host
- User
- MITRE Technique
- NIST CSF Function

Recommended severity colors:

- Critical: red
- High: orange
- Medium: yellow
- Low: gray

### Filters

Keep filters simple:

- Severity
- Status
- Host
- User
- Rule ID
- MITRE Technique ID
- NIST CSF Function
- Time range

### Alert Detail Drawer

When an alert is selected, open a side drawer.

Sections:

1. Summary
   - Title
   - Severity
   - Time
   - Host
   - User
   - Rule ID

2. Framework Mapping
   - NIST CSF function and category
   - MITRE tactic, technique ID, and technique name

3. Evidence
   - Process name
   - Parent process
   - Command line
   - File path
   - Source IP / destination IP if available
   - Raw normalized event JSON

4. Recommended Response
   - Manual checklist from the rule's `response.recommended_actions`

5. Deduplication
   - Dedup key
   - First seen
   - Last seen
   - Suppressed count

6. Optional Enrichment
   - LLM verdict
   - Risk score
   - Suspicious behaviors

### Alert Status

Use simple manual statuses:

- Open
- Investigating
- Benign
- Contained
- Closed

MVP does not need automated response actions.

---

## 3. Rules

### Goal

Let users understand what the daemon can detect and whether each rule is enabled.

### Data Sources

From the daemon guide:

- `rules/*.yml`
- `rule_loader.py`
- `DetectionRule` dataclass
- rule validation results

### Rule Table

Columns:

- Enabled
- Rule ID
- Name
- Severity
- Event Source
- MITRE Technique
- NIST CSF Function
- Has Window
- Dedup Cooldown

Example:

| Enabled | Rule ID | Name | Severity | Event Source | Technique | CSF |
|---|---|---|---|---|---|---|
| Yes | R-001 | Suspicious command interpreter usage | High | process_creation | T1059 | Detect |
| Yes | R-002 | Possible ransomware file encryption activity | Critical | file_activity | T1486 | Detect |

### Rule Detail

Show:

- Basic metadata
- NIST CSF mapping
- MITRE ATT&CK mapping
- Event source
- Logic block
- Window configuration
- Deduplication settings
- Response recommendations
- Raw YAML view

### Rule Actions

MVP actions:

- Enable rule
- Disable rule
- Validate rule
- Reload rules

Later actions:

- Edit rule YAML
- Test rule against a sample event
- Duplicate rule

Keep editing optional. For the first version, read-only YAML plus enable/disable is enough.

---

## 4. Coverage

### Goal

Show what security capabilities and attack techniques are covered.

### Data Sources

From the daemon guide:

- `reports/coverage_report.py`
- enabled rules
- module capability mappings
- alert history

### NIST CSF Coverage

Show a compact table:

| Function | Status | Rules / Modules | Alerts Last 24h |
|---|---|---|---:|
| Govern | Partial | coverage_report | 0 |
| Identify | Yes | process_collector, file_collector | 0 |
| Protect | Partial | allowlists | 0 |
| Detect | Yes | R-001, R-002 | 12 |
| Respond | Yes | alert_handler, playbooks | 12 |
| Recover | Partial | recovery_report | 0 |

Status values:

- Yes
- Partial
- Missing

### MITRE ATT&CK Coverage

Show a table:

| Technique ID | Technique Name | Tactic | Rules | Alerts Last 24h |
|---|---|---|---|---:|
| T1059 | Command and Scripting Interpreter | Execution | R-001 | 9 |
| T1486 | Data Encrypted for Impact | Impact | R-002 | 3 |

Filters:

- Tactic
- Technique ID
- Has alerts
- Enabled rules only

### Missing Coverage

Show a small list:

- NIST CSF functions with no mapped module.
- ATT&CK techniques planned but not implemented.
- Disabled rules.
- Rules with validation errors.

---

## Recommended Data API

The UI can be implemented as a lightweight local web interface.

Recommended backend:

- FastAPI
- SQLite or JSONL readers
- Read-only mode first

Recommended endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Daemon status, queue metrics, collector health |
| `GET /api/alerts` | Paginated alert list |
| `GET /api/alerts/{id}` | Alert details |
| `PATCH /api/alerts/{id}` | Update manual alert status |
| `GET /api/rules` | Rule list |
| `GET /api/rules/{id}` | Rule details |
| `POST /api/rules/reload` | Reload rules |
| `PATCH /api/rules/{id}` | Enable or disable rule |
| `GET /api/coverage/csf` | NIST CSF coverage |
| `GET /api/coverage/mitre` | MITRE ATT&CK coverage |

Keep admin endpoints local-only by default.

---

## Recommended Frontend Layout

Use a simple application shell:

```text
Top Bar
  Product name
  Daemon status badge
  Last refresh time

Left or Top Navigation
  Dashboard
  Alerts
  Rules
  Coverage

Main Content
  Table-first operational views
  Side drawer for details
```

For a compact UI, top navigation is enough.

---

## MVP Screen Priority

Build in this order:

1. Dashboard
2. Alerts
3. Rules
4. Coverage

The Dashboard proves the daemon is alive. Alerts prove detections are useful. Rules make the system understandable. Coverage connects the system back to NIST CSF and MITRE ATT&CK.

---

## MVP Definition of Done

The UI MVP is complete when it can:

- Show daemon running/stopped status.
- Show queue depth and overflow count.
- Show collector health.
- Show recent alerts.
- Filter alerts by severity, host, rule, MITRE technique, and NIST CSF function.
- Open alert details with evidence and response recommendations.
- Show enabled and disabled rules.
- Show rule metadata and raw YAML.
- Trigger rule reload.
- Show NIST CSF coverage.
- Show MITRE ATT&CK coverage.

