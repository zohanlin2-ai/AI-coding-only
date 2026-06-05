# Network Packet Monitor UI Specification

## Review Notes

The source Markdown file appears to have a text encoding issue. Many Chinese labels are corrupted, so this English version is a cleaned and reconstructed specification rather than a strict word-for-word translation.

Visible issues found in the source:

- Many headings, table labels, and UI labels are unreadable due to encoding corruption.
- Several HTML snippets contain broken tags, such as incomplete closing `</div>` labels.
- Some JavaScript template strings are malformed.
- The sample detection logic uses `random() < 0.05` / `Math.random() < 0.05`, which is acceptable only for demo data generation, not for real security detection.
- The document mixes UI specification, sample HTML, mock packet generation, and future roadmap in one file. This English version separates product behavior from prototype-only behavior.

---

## 1. Purpose

This document defines a compact UI for a network packet monitoring tool. The UI is intended for developers, SOC analysts, and security engineers who need to inspect live packet-like events, suspicious traffic, DNS activity, active connections, MITRE ATT&CK mappings, and payload details.

The UI should be simple, dense, and operational. It should behave more like a packet console than a dashboard-heavy product page.

---

## 2. High-Level Layout

Recommended layout:

```text
Toolbar
  Filter input | Start/Pause | Clear | Apply Filter | Interface selector | Packet count

Stats Bar
  Packets/sec | Total bytes | Active connections | Suspicious packets | Alerts

Main Area
  Packet Table | Detail Pane

Bottom Tabs
  Alerts | DNS Queries | Connections

Status Bar
  Capture status | Interface | Queue depth | Drops | Current time
```

Recommended dimensions:

- Detail pane width: approximately `320px`.
- Bottom tab pane height: approximately `120px`.
- Packet table should take the remaining horizontal space.
- Packet table should be scrollable and keep the header sticky.

---

## 3. Toolbar

### Controls

| Control | UI Element | Purpose |
|---|---|---|
| Filter input | Text input | Accepts packet filter expressions. |
| Start / Pause | Button | Starts or pauses packet capture display. |
| Clear | Button | Clears current packets and counters. |
| Apply Filter | Button | Applies the filter input. Pressing Enter should also apply it. |
| Interface selector | Select menu | Selects network interface, such as `eth0`, `wlan0`, or `lo`. |
| Packet count | Read-only text | Displays total packets currently loaded in the UI. |

### Example Filter Expressions

```text
ip.src == 10.0.0.5
ip.dst == 185.220.101.47
tcp.port == 4444
proto == DNS
suspicious == true
mitre contains T1059
```

### Capture Button States

| State | Visual Style | Behavior |
|---|---|---|
| Running | Success | Events are being displayed live. |
| Paused | Danger or warning | Capture display is paused. Incoming events may be buffered or ignored depending on backend behavior. |
| Disconnected | Neutral plus warning icon | UI is not connected to the packet event source. |

---

## 4. Stats Bar

Display five compact stat cards.

| Metric | Example | Notes |
|---|---:|---|
| Packets/sec | `128` | Updated once per second. |
| Total bytes | `4.2 MB` | Sum of displayed packet lengths. |
| Active connections | `42` | Count of observed `src:port -> dst:port` pairs. |
| Suspicious packets | `7` | Packets marked suspicious by rule logic. |
| Alerts | `3` | Alert-level events generated from suspicious traffic. |

Use compact typography. Numeric values should be easy to scan.

---

## 5. Suspicious Traffic Logic

The UI may show suspicious status, but the real detection logic should live in the backend.

Prototype-only example:

```python
SUSPICIOUS_IPS = [
    "185.220.101.47",
    "23.95.110.24",
    "91.108.4.1",
    "104.21.66.213",
]

SUSPICIOUS_PORTS = [4444, 1337, 31337, 6667, 12345]


def is_suspicious(packet) -> bool:
    return (
        packet.dst in SUSPICIOUS_IPS
        or packet.dport in SUSPICIOUS_PORTS
    )
```

Do not use randomness as a real suspicious signal. Random suspicious flags are acceptable only in demo packet generation.

Recommended backend detection signals:

- Known suspicious destination IP.
- Known suspicious destination port.
- Non-standard port for protocol.
- DNS query using punycode or suspicious TLD.
- Unusual outbound connection.
- MITRE ATT&CK rule match.
- Threat intelligence match.

---

## 6. Packet Table

### Columns

| Column | Width | Description |
|---|---:|---|
| `#` | `42px` | Packet sequence number. |
| Time | `80px` | Format: `HH:MM:SS.mmm`. |
| Source IP | `110px` | Source IP address. |
| Destination IP | `110px` | Destination IP address. |
| Protocol | `64px` | Protocol badge. |
| Length | `52px` | Packet length in bytes. |
| Summary | Flexible | Short packet summary. Truncate overflow with ellipsis. |

### Protocol Badge Styles

| Protocol | Style | Meaning |
|---|---|---|
| TCP | Info | Standard TCP traffic. |
| UDP | Success | Standard UDP traffic. |
| DNS | Warning | DNS traffic, may require analyst review. |
| HTTP | Secondary | Plain HTTP traffic. |
| TLS | Info | TLS traffic. |
| SUSPICIOUS | Danger | Traffic matched suspicious criteria. |

### Row States

| Row State | Style | Meaning |
|---|---|---|
| Normal | Default | No suspicious signal. |
| Warning | Warning text or background | Suspicious DNS or unusual behavior. |
| Danger | Danger text or background | High-confidence suspicious traffic. |
| Selected | Highlighted background | Packet currently selected in detail pane. |

### Behavior

- Clicking a row opens the packet detail pane.
- The table should keep only the latest visible rows for performance, such as the latest 80 packets.
- Filtering should update the packet table without clearing stored packets.
- Long summaries should use ellipsis instead of wrapping.

---

## 7. Detail Pane

The detail pane shows the selected packet. It should be approximately `320px` wide.

### Sections

#### 7.1 Packet Summary

```text
Packet #[sequence]
Time      HH:MM:SS.mmm
Protocol  TCP / UDP / DNS / HTTP / TLS / SUSPICIOUS
Length    N bytes
```

#### 7.2 Network Fields

```text
Source       IP:Port
Destination  IP:Port
TTL          N
```

#### 7.3 MITRE ATT&CK

Show this section only when a MITRE technique is available.

Example:

```text
T1059.001 - PowerShell
T1571 - Non-Standard Port
T1568 - Dynamic Resolution
```

#### 7.4 Payload

Payload should use monospace text. It should wrap safely and preserve readability.

Example:

```text
powershell -enc SQBFAFgAKABOAGUAdwAtAE8AYgBqAGUAYwB0ACkA
```

#### 7.5 AI Analysis

Optional. Add a manual button:

```text
Analyze with AI
```

AI analysis should not run automatically for every packet. It should be available for suspicious payloads, scripts, or analyst-selected packets.

---

## 8. Bottom Tabs

The bottom panel should be compact and fixed-height.

### Tab 1: Alerts

Shows recent alert lines.

Example:

```text
[10:30:00.123] T1059.001 detected from 10.0.0.5:52341 to 185.220.101.47:4444
[10:30:02.882] Suspicious DNS query: xn--malw4r3.cc from 10.0.0.12
```

Alert severity styles:

- Danger: high-confidence suspicious traffic.
- Warning: suspicious DNS or weak signal.
- Info: normal operational messages.

### Tab 2: DNS Queries

Shows DNS query activity.

Example:

```text
[10:30:01.000] 10.0.0.5  -> google.com
[10:30:02.882] 10.0.0.12 -> xn--malw4r3.cc [Suspicious]
```

Suspicious DNS indicators:

- Punycode domain, such as `xn--`.
- Suspicious TLD, such as `.cc`, `.tk`, or `.xyz`.
- Dynamic DNS or redirector-style domains.
- IP-encoded domains, such as `xip.io` or `nip.io`.

### Tab 3: Connections

Shows observed active connections.

Example:

```text
CONN  10.0.0.5:52341 -> 185.220.101.47:4444
CONN  10.0.0.12:34821 -> 8.8.8.8:53
```

---

## 9. Status Bar

Example:

```text
Running | eth0 | Queue: 3 | Drops: 0 | 10:30:00.123
```

Fields:

| Field | Description |
|---|---|
| Capture status | Running, paused, or disconnected. |
| Interface | Current selected network interface. |
| Queue depth | Number of pending events in the frontend or backend queue. |
| Drops | Number of dropped packets or events. |
| Time | Current local time or last event time. |

---

## 10. Color Tokens

Use semantic color tokens instead of hard-coded colors throughout the UI.

| Token | Usage |
|---|---|
| `danger` | Suspicious packet, suspicious IP, high-confidence alert. |
| `warning` | Suspicious DNS, unusual but lower-confidence activity. |
| `success` | Running state, normal UDP badge. |
| `info` | TCP/TLS badge, ordinary network metadata. |
| `secondary` | Normal HTTP or neutral information. |

Support light and dark mode with the same semantic token names.

---

## 11. Typography

| Use Case | Font |
|---|---|
| General UI | System sans-serif. |
| IP addresses, ports, payloads, packet table | Monospace. |
| Stat values | Monospace, medium weight, approximately `18px`. |

The packet table may use monospace for better alignment and scanning.

---

## 12. Refresh and Performance

Recommended refresh behavior:

| UI Area | Refresh Strategy |
|---|---|
| Packet table | Update when new events arrive. |
| Packets/sec | Update every 1 second. |
| Clock | Update every 1 second. |
| Queue depth | Update every tick or every 1 second. |
| Bottom tabs | Update when new related events arrive. |

The interface must receive real active network connection events from the system daemon.

Performance notes:

- Render only the latest visible rows, such as 80 to 200 rows.
- Store full packet history in backend storage, not only in the browser.
- Avoid re-rendering the entire page on every packet if traffic volume is high.
- Use virtualized rows if the table needs to display thousands of packets.

---

## 13. Data Model

Recommended frontend packet event model:

```python
from dataclasses import dataclass


@dataclass
class PacketEvent:
    seq: int
    time: str              # ISO 8601 or HH:MM:SS.mmm for display
    src: str               # Source IP
    dst: str               # Destination IP
    sport: int
    dport: int
    proto: str             # TCP / UDP / DNS / TLS / HTTP / SUSPICIOUS
    length: int
    summary: str
    payload: str
    mitre: str | None      # MITRE ATT&CK technique ID and name
    is_suspicious: bool
```

Recommended JSON event:

```json
{
  "type": "packet",
  "data": {
    "seq": 1024,
    "time": "2026-06-05T10:30:00.123Z",
    "src": "10.0.0.5",
    "dst": "185.220.101.47",
    "sport": 52341,
    "dport": 4444,
    "proto": "SUSPICIOUS",
    "length": 248,
    "summary": "powershell -enc SQBFAFgA...",
    "payload": "powershell -enc SQBFAFgA...",
    "mitre": "T1059.001 - PowerShell",
    "is_suspicious": true
  }
}
```

---

## 14. Backend Integration Options

### Option A: WebSocket

Recommended for live monitoring.

Behavior:

- Python daemon exposes a FastAPI WebSocket endpoint.
- Browser subscribes to packet events.
- Backend pushes packets as they arrive.

Example endpoint:

```text
WS /ws/packets
```

### Option B: Server-Sent Events

Good for one-way streaming from backend to UI.

Example endpoint:

```text
GET /api/packets/stream
```

### Option C: HTTP Polling

Simplest fallback.

Example endpoint:

```text
GET /api/packets?since=last_seq
```

Use polling only if WebSocket or SSE is not available.

---

## 15. Recommended API

| Endpoint | Purpose |
|---|---|
| `GET /api/status` | Capture status, interface, queue depth, drops, current time. |
| `GET /api/interfaces` | Available network interfaces. |
| `POST /api/capture/start` | Start capture. |
| `POST /api/capture/pause` | Pause capture. |
| `GET /api/packets?since={seq}` | Fetch packets after a sequence number. |
| `GET /api/packets/{seq}` | Fetch packet detail. |
| `GET /api/alerts` | Fetch alert log. |
| `GET /api/dns` | Fetch recent DNS queries. |
| `GET /api/connections` | Fetch active connections. |
| `POST /api/analysis/packet/{seq}` | Run optional AI analysis for a selected packet. |

For local desktop use, bind admin APIs to localhost by default.

---

## 16. HTML Prototype Guidance

The source file contains a single-file HTML prototype. That is useful for visual testing, but production code should separate:

- HTML structure.
- CSS tokens and layout.
- JavaScript state management.
- Backend API client.
- Mock packet generator.

Recommended file layout for a prototype:

```text
network-packet-monitor/
  index.html
  styles.css
  app.js
  mock-data.js
```

Recommended file layout for a full app:

```text
network-packet-monitor/
  backend/
    main.py
    capture.py
    models.py
    detection.py
  frontend/
    src/
      App.tsx
      api.ts
      components/
        Toolbar.tsx
        StatsBar.tsx
        PacketTable.tsx
        DetailPane.tsx
        BottomTabs.tsx
        StatusBar.tsx
```

---

## 17. Future Enhancements

| Feature | Description | Priority |
|---|---|---|
| WebSocket integration | Replace mock packet generation with live backend events. | High |
| Packet graph | Add a compact connection graph for source/destination relationships. | Medium |
| Filter parser | Convert filter expressions into structured query logic. | Medium |
| Packet export | Export selected packets to JSON or PCAP-compatible format. | Medium |
| AI packet analysis | Analyze selected suspicious payloads through an external analysis service. | Medium |
| Alert rule management | Manage YAML-based packet detection rules from the UI. | Low |

---

## 18. MVP Definition of Done

The UI MVP is complete when it can:

- Show live packet events.
- Pause and resume packet display.
- Clear packet history in the UI.
- Filter packets by simple text search.
- Display packet stats.
- Mark suspicious packets clearly.
- Show packet details in a side pane.
- Show MITRE ATT&CK technique mappings when available.
- Show recent alerts.
- Show DNS queries.
- Show active connections.
- Show capture status, queue depth, dropped events, and current time.

