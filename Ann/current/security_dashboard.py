"""
security_dashboard.py — Security Dashboard widget for Ann's chat window.

Displayed when Ann is in security monitoring mode (toggled via [SECURITY_ON] /
[SECURITY_OFF] markers).  Uses mock data in Phase 1; Phase 2 will read from
the real security daemon's alerts.jsonl / SQLite store.

Layout:
  ┌─────────────────────────────────────┐
  │  StatusCard  StatusCard  StatusCard  │  ← top row: 3 compact stat cards
  ├─────────────────────────────────────┤
  │  Alert Feed (scrollable compact     │
  │  list — click row to expand detail) │
  └─────────────────────────────────────┘
"""
from __future__ import annotations

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
        QScrollArea, QSizePolicy,
    )
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QColor
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
        QScrollArea, QSizePolicy,
    )
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor


# ---------------------------------------------------------------------------
# Mock data (Phase 1) — replace with real daemon reads in Phase 2
# ---------------------------------------------------------------------------

_MOCK_ALERTS = [
    {
        "id": "A-001",
        "rule_id": "R-001",
        "title": "Suspicious PowerShell Execution",
        "severity": "high",
        "mitre": "T1059",
        "host": "WIN-ENDPOINT-01",
        "user": "alice",
        "time": "16:23:41",
        "status": "open",
        "evidence": "powershell.exe -enc IEX(New-Object Net.WebClient)...",
        "response": [
            "Review command line and parent process.",
            "Check user account context.",
        ],
    },
    {
        "id": "A-002",
        "rule_id": "R-002",
        "title": "Rapid File Modification (Ransomware-Like)",
        "severity": "critical",
        "mitre": "T1486",
        "host": "WIN-ENDPOINT-01",
        "user": "alice",
        "time": "16:21:05",
        "status": "open",
        "evidence": "600 file modifications in 5 min, 120 extension changes (.locked)",
        "response": [
            "Isolate affected endpoint immediately.",
            "Disable suspected user account.",
            "Validate backup availability.",
        ],
    },
    {
        "id": "A-003",
        "rule_id": "R-001",
        "title": "Suspicious PowerShell Execution",
        "severity": "high",
        "mitre": "T1059",
        "host": "WIN-ENDPOINT-02",
        "user": "bob",
        "time": "15:58:12",
        "status": "investigating",
        "evidence": "powershell.exe Invoke-WebRequest http://...",
        "response": ["Review command line and parent process."],
    },
    {
        "id": "A-004",
        "rule_id": "R-001",
        "title": "Suspicious Shell Interpreter",
        "severity": "medium",
        "mitre": "T1059",
        "host": "WIN-ENDPOINT-03",
        "user": "charlie",
        "time": "15:30:00",
        "status": "benign",
        "evidence": "cmd.exe /c curl http://internal-endpoint/healthcheck",
        "response": ["Review command line context."],
    },
]

_SEVERITY_COLORS = {
    "critical": "#E53E3E",
    "high":     "#ED8936",
    "medium":   "#ECC94B",
    "low":      "#A0AEC0",
}

_STATUS_COLORS = {
    "open":          "#FC8181",
    "investigating": "#F6AD55",
    "benign":        "#68D391",
    "contained":     "#63B3ED",
    "closed":        "#A0AEC0",
}


# ---------------------------------------------------------------------------
# StatusCard — compact metric tile
# ---------------------------------------------------------------------------

class _StatusCard(QFrame):
    def __init__(self, label: str, value: str, accent: str = "#63B3ED", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background-color: #1E2330; border: 1px solid {accent}44; "
            f"border-left: 3px solid {accent}; border-radius: 8px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(
            f"color: {accent}; font-size: 18px; font-weight: bold; "
            f"font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(val_lbl)

        key_lbl = QLabel(label)
        key_lbl.setStyleSheet(
            "color: #718096; font-size: 10px; font-family: 'Segoe UI'; "
            "border: none; background: transparent;"
        )
        key_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(key_lbl)


# ---------------------------------------------------------------------------
# AlertFeedItem — one row in the compact alert feed
# ---------------------------------------------------------------------------

class _AlertFeedItem(QFrame):
    """
    Compact single-line alert row.  Click to toggle an expanded detail section.
    """

    def __init__(self, alert: dict, parent=None):
        super().__init__(parent)
        self._alert = alert
        self._expanded = False

        severity = alert.get("severity", "low")
        accent = _SEVERITY_COLORS.get(severity, "#A0AEC0")

        # Outer border: left-coloured stripe for critical/high
        self.setStyleSheet(
            f"QFrame {{ background-color: #1A1D24; border: none; "
            f"border-left: 3px solid {accent}; border-radius: 0px; }}"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(8, 6, 8, 6)
        self._outer.setSpacing(0)

        # ── Summary row ──────────────────────────────────────────────────
        row = QHBoxLayout()
        row.setSpacing(8)

        dot = QLabel("●")
        dot.setFixedWidth(14)
        dot.setStyleSheet(
            f"color: {accent}; font-size: 10px; border: none; background: transparent;"
        )
        row.addWidget(dot)

        title_lbl = QLabel(alert.get("title", ""))
        title_lbl.setStyleSheet(
            "color: #E2E8F0; font-size: 12px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(title_lbl)

        meta = QLabel(
            f"{alert.get('time', '')}  ·  {alert.get('host', '')}  ·  {alert.get('mitre', '')}"
        )
        meta.setStyleSheet(
            "color: #718096; font-size: 10px; font-family: 'Segoe UI'; "
            "border: none; background: transparent;"
        )
        meta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(meta)

        status_text = alert.get("status", "open")
        status_color = _STATUS_COLORS.get(status_text, "#A0AEC0")
        status_lbl = QLabel(status_text.upper())
        status_lbl.setFixedWidth(90)
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lbl.setStyleSheet(
            f"color: {status_color}; font-size: 9px; font-weight: bold; "
            f"font-family: 'Segoe UI'; border: 1px solid {status_color}44; "
            f"border-radius: 4px; padding: 1px 4px; background: transparent;"
        )
        row.addWidget(status_lbl)

        self._outer.addLayout(row)

        # ── Detail section (hidden by default) ───────────────────────────
        self._detail_widget = QWidget()
        self._detail_widget.setStyleSheet("background: transparent;")
        detail_layout = QVBoxLayout(self._detail_widget)
        detail_layout.setContentsMargins(22, 6, 0, 4)
        detail_layout.setSpacing(3)

        for line, color in [
            (f"Evidence:  {alert.get('evidence', '')}", "#A0AEC0"),
        ]:
            lbl = QLabel(line)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"color: {color}; font-size: 11px; font-family: 'Segoe UI'; "
                f"border: none; background: transparent;"
            )
            detail_layout.addWidget(lbl)

        for action in alert.get("response", []):
            a_lbl = QLabel(f"→ {action}")
            a_lbl.setWordWrap(True)
            a_lbl.setStyleSheet(
                "color: #68D391; font-size: 11px; font-family: 'Segoe UI'; "
                "border: none; background: transparent;"
            )
            detail_layout.addWidget(a_lbl)

        self._detail_widget.hide()
        self._outer.addWidget(self._detail_widget)

    def mousePressEvent(self, event) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            self._detail_widget.show()
        else:
            self._detail_widget.hide()
        event.accept()


# ---------------------------------------------------------------------------
# SecurityDashboardWidget — the top-level widget swapped into ChatWindow
# ---------------------------------------------------------------------------

class SecurityDashboardWidget(QWidget):
    """
    Full Security Dashboard.  Instantiated once and kept alive inside a
    QStackedWidget in ChatWindow.  Call refresh() to reload mock (or real) data.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(8)

        # ── Header label ──────────────────────────────────────────────────
        header = QLabel("🛡️  Security Dashboard")
        header.setStyleSheet(
            "color: #FC8181; font-size: 13px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        root.addWidget(header)

        # ── Status cards row ──────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(6)

        self._daemon_card  = _StatusCard("DAEMON",    "Running",  "#68D391")
        self._queue_card   = _StatusCard("QUEUE",     "12 / 10K", "#63B3ED")
        self._alerts_card  = _StatusCard("ALERTS/HR", "4 (1 🔴)", "#FC8181")

        for card in (self._daemon_card, self._queue_card, self._alerts_card):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cards_row.addWidget(card)

        root.addLayout(cards_row)

        # ── Divider ───────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #2D3748; background-color: #2D3748; border: none;")
        divider.setFixedHeight(1)
        root.addWidget(divider)

        # ── Alert feed (scrollable) ───────────────────────────────────────
        feed_label = QLabel("Recent Alerts")
        feed_label.setStyleSheet(
            "color: #718096; font-size: 10px; font-family: 'Segoe UI'; "
            "border: none; background: transparent;"
        )
        root.addWidget(feed_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background-color: transparent; }"
            "QScrollBar:vertical { border: none; background: #1A1D24; width: 6px; }"
            "QScrollBar::handle:vertical { background: #4A5568; border-radius: 3px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )

        self._feed_container = QWidget()
        self._feed_container.setStyleSheet("background-color: transparent;")
        self._feed_layout = QVBoxLayout(self._feed_container)
        self._feed_layout.setContentsMargins(0, 0, 0, 0)
        self._feed_layout.setSpacing(1)
        self._feed_layout.addStretch()

        scroll.setWidget(self._feed_container)
        root.addWidget(scroll)

        # ── Auto-refresh every 30 s (Phase 2 will call real API) ─────────
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(30_000)
        self._refresh_timer.timeout.connect(self.refresh)

        self.refresh()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_monitoring(self) -> None:
        """Call when security mode is entered."""
        self._refresh_timer.start()

    def stop_monitoring(self) -> None:
        """Call when security mode is exited."""
        self._refresh_timer.stop()

    def refresh(self) -> None:
        """Reload alert feed. Phase 2: replace _MOCK_ALERTS with real reads."""
        # Clear existing items (keep the trailing stretch)
        while self._feed_layout.count() > 1:
            item = self._feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Sort by severity priority then time (mock data is already ordered)
        priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts = sorted(_MOCK_ALERTS, key=lambda a: priority.get(a.get("severity", "low"), 4))

        for alert in alerts:
            row = _AlertFeedItem(alert)
            self._feed_layout.insertWidget(self._feed_layout.count() - 1, row)

            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #2D3748; background-color: #2D3748; border: none;")
            sep.setFixedHeight(1)
            self._feed_layout.insertWidget(self._feed_layout.count() - 1, sep)
