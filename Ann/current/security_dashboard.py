"""
security_dashboard.py — Security Dashboard widget for Ann's chat window.

Four views via a compact nav bar (no tabs):
  概覽 | 告警 | 規則 | 覆蓋率

Daemon is always running by default.  Start / Stop controls are only
accessible from within Security Mode (this widget is only shown then).
On Ann restart/update, _daemon_running resets to True automatically.

Phase 1: mock data.  Phase 2: replace _MOCK_* with real daemon reads.
"""
from __future__ import annotations

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
        QScrollArea, QSizePolicy, QPushButton, QStackedWidget,
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
        QScrollArea, QSizePolicy, QPushButton, QStackedWidget,
    )
    from PySide6.QtCore import Qt, QTimer, Signal
    pyqtSignal = Signal


# ---------------------------------------------------------------------------
# Mock data  (Phase 2: replace with real alerts.jsonl / SQLite reads)
# ---------------------------------------------------------------------------

_MOCK_ALERTS = [
    {
        "id": "A-001", "rule_id": "R-001",
        "title": "Suspicious PowerShell Execution",
        "severity": "high", "mitre": "T1059",
        "host": "WIN-ENDPOINT-01", "user": "alice", "time": "16:23:41",
        "status": "open",
        "evidence": "powershell.exe -enc IEX(New-Object Net.WebClient)...",
        "response": ["Review command line and parent process.", "Check user account context."],
    },
    {
        "id": "A-002", "rule_id": "R-002",
        "title": "Rapid File Modification (Ransomware-Like)",
        "severity": "critical", "mitre": "T1486",
        "host": "WIN-ENDPOINT-01", "user": "alice", "time": "16:21:05",
        "status": "open",
        "evidence": "600 file modifications in 5 min, 120 extension changes (.locked)",
        "response": [
            "Isolate affected endpoint immediately.",
            "Disable suspected user account.",
            "Validate backup availability.",
        ],
    },
    {
        "id": "A-003", "rule_id": "R-001",
        "title": "Suspicious PowerShell Execution",
        "severity": "high", "mitre": "T1059",
        "host": "WIN-ENDPOINT-02", "user": "bob", "time": "15:58:12",
        "status": "investigating",
        "evidence": "powershell.exe Invoke-WebRequest http://...",
        "response": ["Review command line and parent process."],
    },
    {
        "id": "A-004", "rule_id": "R-001",
        "title": "Suspicious Shell Interpreter",
        "severity": "medium", "mitre": "T1059",
        "host": "WIN-ENDPOINT-03", "user": "charlie", "time": "15:30:00",
        "status": "benign",
        "evidence": "cmd.exe /c curl http://internal-endpoint/healthcheck",
        "response": ["Review command line context."],
    },
    {
        "id": "A-005", "rule_id": "R-002",
        "title": "Rapid File Modification (Ransomware-Like)",
        "severity": "critical", "mitre": "T1486",
        "host": "WIN-ENDPOINT-04", "user": "dave", "time": "14:55:30",
        "status": "contained",
        "evidence": "520 file modifications, .encrypted extension changes",
        "response": ["Host isolated. Backup validated."],
    },
]

_MOCK_RULES = [
    {
        "id": "R-001", "name": "Suspicious Command Interpreter",
        "severity": "high", "source": "process_creation",
        "mitre_id": "T1059", "mitre_name": "Command and Scripting Interpreter",
        "csf": "Detect", "enabled": True, "has_window": False, "dedup_cooldown": 300,
    },
    {
        "id": "R-002", "name": "Ransomware File Encryption",
        "severity": "critical", "source": "file_activity",
        "mitre_id": "T1486", "mitre_name": "Data Encrypted for Impact",
        "csf": "Detect", "enabled": True, "has_window": True, "dedup_cooldown": 600,
    },
    {
        "id": "R-003", "name": "Network Connection to Suspicious IP",
        "severity": "medium", "source": "network_activity",
        "mitre_id": "T1071", "mitre_name": "Application Layer Protocol",
        "csf": "Detect", "enabled": True, "has_window": False, "dedup_cooldown": 180,
    },
]

_MOCK_CSF = [
    {"function": "Govern",   "status": "missing", "coverage": "—",                      "alerts": 0},
    {"function": "Identify", "status": "partial", "coverage": "ProcessCollector",        "alerts": 0},
    {"function": "Protect",  "status": "partial", "coverage": "Allowlists",              "alerts": 0},
    {"function": "Detect",   "status": "yes",     "coverage": "R-001, R-002, R-003",     "alerts": 12},
    {"function": "Respond",  "status": "yes",     "coverage": "AlertHandler, Playbooks", "alerts": 12},
    {"function": "Recover",  "status": "missing", "coverage": "—",                       "alerts": 0},
]

_MOCK_MITRE = [
    {"id": "T1059", "name": "Command and Scripting Interpreter", "tactic": "Execution", "rules": "R-001", "alerts": 9},
    {"id": "T1486", "name": "Data Encrypted for Impact",         "tactic": "Impact",    "rules": "R-002", "alerts": 3},
    {"id": "T1071", "name": "Application Layer Protocol",        "tactic": "C2",        "rules": "R-003", "alerts": 0},
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

_CSF_STATUS_COLORS = {
    "yes":     "#68D391",
    "partial": "#F6AD55",
    "missing": "#FC8181",
}

_SEVERITY_PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ---------------------------------------------------------------------------
# _NavButton — compact segmented-control style button
# ---------------------------------------------------------------------------

class _NavButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setActive(False)

    def setActive(self, active: bool) -> None:
        if active:
            self.setStyleSheet(
                "QPushButton { color: #E2E8F0; background-color: #2D3748; "
                "border: 1px solid #4A5568; border-radius: 6px; "
                "padding: 3px 8px; font-size: 11px; font-family: 'Segoe UI'; font-weight: bold; }"
            )
        else:
            self.setStyleSheet(
                "QPushButton { color: #718096; background-color: transparent; "
                "border: 1px solid transparent; border-radius: 6px; "
                "padding: 3px 8px; font-size: 11px; font-family: 'Segoe UI'; }"
                "QPushButton:hover { color: #A0AEC0; border-color: #4A5568; }"
            )


# ---------------------------------------------------------------------------
# _AlertFeedItem — single alert row, click to expand detail
# ---------------------------------------------------------------------------

class _AlertFeedItem(QFrame):
    def __init__(self, alert: dict, compact: bool = False, parent=None):
        super().__init__(parent)
        self._expanded = False
        severity = alert.get("severity", "low")
        accent = _SEVERITY_COLORS.get(severity, "#A0AEC0")

        self.setStyleSheet(
            f"QFrame {{ background-color: #1A1D24; border: none; "
            f"border-left: 3px solid {accent}; }}"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 5, 8, 5)
        outer.setSpacing(0)

        # Summary row
        row = QHBoxLayout()
        row.setSpacing(6)

        dot = QLabel("●")
        dot.setFixedWidth(12)
        dot.setStyleSheet(f"color: {accent}; font-size: 9px; border: none; background: transparent;")
        row.addWidget(dot)

        title_lbl = QLabel(alert.get("title", ""))
        title_lbl.setStyleSheet(
            "color: #E2E8F0; font-size: 11px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(title_lbl)

        time_txt = alert.get("time", "")
        if not compact:
            time_txt = f"{time_txt} · {alert.get('host', '')}"
        meta = QLabel(time_txt)
        meta.setStyleSheet(
            "color: #718096; font-size: 10px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        meta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(meta)

        status_text = alert.get("status", "open")
        status_color = _STATUS_COLORS.get(status_text, "#A0AEC0")
        status_lbl = QLabel(status_text.upper())
        status_lbl.setFixedWidth(82)
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lbl.setStyleSheet(
            f"color: {status_color}; font-size: 9px; font-weight: bold; "
            f"border: 1px solid {status_color}44; border-radius: 4px; "
            f"padding: 1px 4px; background: transparent;"
        )
        row.addWidget(status_lbl)
        outer.addLayout(row)

        # MITRE / host sub-line
        sub_row = QHBoxLayout()
        sub_row.setContentsMargins(18, 0, 0, 0)
        sub_lbl = QLabel(
            f"MITRE {alert.get('mitre', '')}  ·  {alert.get('host', '')}  ·  {alert.get('user', '')}"
        )
        sub_lbl.setStyleSheet(
            "color: #4A5568; font-size: 9px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        sub_row.addWidget(sub_lbl)
        sub_row.addStretch()
        outer.addLayout(sub_row)

        # Detail section (hidden until click)
        self._detail = QWidget()
        self._detail.setStyleSheet("background: transparent;")
        d_layout = QVBoxLayout(self._detail)
        d_layout.setContentsMargins(18, 4, 0, 4)
        d_layout.setSpacing(2)

        ev_lbl = QLabel(f"Evidence:  {alert.get('evidence', '')}")
        ev_lbl.setWordWrap(True)
        ev_lbl.setStyleSheet(
            "color: #A0AEC0; font-size: 10px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        d_layout.addWidget(ev_lbl)

        for action in alert.get("response", []):
            a_lbl = QLabel(f"→  {action}")
            a_lbl.setWordWrap(True)
            a_lbl.setStyleSheet(
                "color: #68D391; font-size: 10px; font-family: 'Segoe UI'; border: none; background: transparent;"
            )
            d_layout.addWidget(a_lbl)

        self._detail.hide()
        outer.addWidget(self._detail)

    def mousePressEvent(self, event) -> None:
        self._expanded = not self._expanded
        self._detail.setVisible(self._expanded)
        event.accept()


# ---------------------------------------------------------------------------
# SecurityDashboardWidget
# ---------------------------------------------------------------------------

class SecurityDashboardWidget(QWidget):
    """
    Four-view security dashboard embedded in Ann's ChatWindow via QStackedWidget.

    Signals:
        alert_triggered(severity, title) — emitted when a new critical/high
            alert is detected.  ChatWindow connects this to add a chat message
            and nudge the FloatingBubble.
    """

    alert_triggered = pyqtSignal(str, str)  # (severity, title)

    def __init__(self, config: dict = None, parent=None):
        super().__init__(parent)
        self.config = config or {}
        # Get daemon singleton instance
        from security_daemon import SecurityDaemon
        self.daemon = SecurityDaemon(self.config)
        self._daemon_running = self.daemon.running

        # IDs already notified in this session — avoids duplicate notifications.
        self._notified_ids: set[str] = set()
        # Current severity filter in Alerts view (None = ALL).
        self._active_filter: str | None = None
        # Per-rule enabled state (editable in Rules view, mock only in Phase 1).
        self._rule_states: dict[str, bool] = {r["id"]: r["enabled"] for r in _MOCK_RULES}

        self.setStyleSheet("background-color: transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(5)

        # Header
        hdr = QLabel("🛡️  Security Dashboard")
        hdr.setStyleSheet(
            "color: #FC8181; font-size: 13px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        root.addWidget(hdr)

        # Nav bar (4 compact buttons, no tabs)
        nav_widget = QWidget()
        nav_widget.setStyleSheet("background: transparent;")
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)

        self._nav_btns: list[_NavButton] = []
        for i, label in enumerate(["🏠 概覽", "📋 告警", "📜 規則", "🛡 覆蓋率"]):
            btn = _NavButton(label)
            btn.setActive(i == 0)
            btn.clicked.connect(lambda _checked, x=i: self._switch_view(x))
            nav_layout.addWidget(btn)
            self._nav_btns.append(btn)
        nav_layout.addStretch()
        root.addWidget(nav_widget)

        # Content stack — four views
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_overview())   # 0
        self._stack.addWidget(self._build_alerts())     # 1
        self._stack.addWidget(self._build_rules())      # 2
        self._stack.addWidget(self._build_coverage())   # 3
        root.addWidget(self._stack)

        # 5-second refresh timer (Phase 2: poll real data)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(5_000)
        self._refresh_timer.timeout.connect(self.refresh)

        # First alert check fires 2 s after entering security mode
        self._notification_timer = QTimer(self)
        self._notification_timer.setSingleShot(True)
        self._notification_timer.setInterval(2_000)
        self._notification_timer.timeout.connect(self._check_new_alerts)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _switch_view(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setActive(i == index)

    # ------------------------------------------------------------------
    # View 0 — Overview
    # ------------------------------------------------------------------

    def _build_overview(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Notification banner (hidden until an alert fires)
        self._notif_banner = QFrame()
        self._notif_banner.setStyleSheet(
            "QFrame { background-color: #3D1515; border: 1px solid #E53E3E; border-radius: 6px; }"
        )
        nb_layout = QHBoxLayout(self._notif_banner)
        nb_layout.setContentsMargins(8, 5, 8, 5)
        self._notif_label = QLabel("🚨 New critical alert detected")
        self._notif_label.setStyleSheet(
            "color: #FC8181; font-size: 11px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        nb_layout.addWidget(self._notif_label)
        nb_layout.addStretch()
        dismiss_x = QPushButton("✕")
        dismiss_x.setFixedSize(18, 18)
        dismiss_x.setStyleSheet(
            "QPushButton { color: #FC8181; border: none; background: transparent; font-size: 12px; }"
            "QPushButton:hover { color: white; }"
        )
        dismiss_x.clicked.connect(self._notif_banner.hide)
        nb_layout.addWidget(dismiss_x)
        self._notif_banner.hide()
        layout.addWidget(self._notif_banner)

        # ── Status cards ─────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(6)

        # Daemon card (with Start/Stop toggle — only reachable in security mode)
        daemon_frame = QFrame()
        daemon_frame.setStyleSheet(
            "QFrame { background-color: #1E2330; border: 1px solid #68D39144; "
            "border-left: 3px solid #68D391; border-radius: 8px; }"
        )
        daemon_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        df_layout = QVBoxLayout(daemon_frame)
        df_layout.setContentsMargins(10, 8, 10, 8)
        df_layout.setSpacing(2)

        self._daemon_val_lbl = QLabel("Running")
        self._daemon_val_lbl.setStyleSheet(
            "color: #68D391; font-size: 16px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        df_layout.addWidget(self._daemon_val_lbl)

        daemon_key = QLabel("DAEMON")
        daemon_key.setStyleSheet(
            "color: #718096; font-size: 10px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        df_layout.addWidget(daemon_key)

        self._daemon_toggle_btn = QPushButton("⏹ Stop")
        self._daemon_toggle_btn.setStyleSheet(
            "QPushButton { color: #FC8181; background: transparent; "
            "border: 1px solid #FC818155; border-radius: 4px; "
            "font-size: 10px; padding: 2px 6px; font-family: 'Segoe UI'; }"
            "QPushButton:hover { background-color: #3D1515; }"
        )
        self._daemon_toggle_btn.clicked.connect(self._toggle_daemon)
        df_layout.addWidget(self._daemon_toggle_btn)
        cards_row.addWidget(daemon_frame)

        # Queue card
        queue_frame = QFrame()
        queue_frame.setStyleSheet(
            "QFrame { background-color: #1E2330; border: 1px solid #63B3ED44; "
            "border-left: 3px solid #63B3ED; border-radius: 8px; }"
        )
        queue_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        qf = QVBoxLayout(queue_frame)
        qf.setContentsMargins(10, 8, 10, 8)
        qf.setSpacing(2)
        q_val = QLabel("12 / 10K")
        q_val.setStyleSheet(
            "color: #63B3ED; font-size: 16px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        qf.addWidget(q_val)
        q_key = QLabel("QUEUE")
        q_key.setStyleSheet(
            "color: #718096; font-size: 10px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        qf.addWidget(q_key)
        cards_row.addWidget(queue_frame)

        # Alerts/hr card
        alerts_frame = QFrame()
        alerts_frame.setStyleSheet(
            "QFrame { background-color: #1E2330; border: 1px solid #FC818144; "
            "border-left: 3px solid #FC8181; border-radius: 8px; }"
        )
        alerts_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        af = QVBoxLayout(alerts_frame)
        af.setContentsMargins(10, 8, 10, 8)
        af.setSpacing(2)
        a_val = QLabel("4  (2🔴)")
        a_val.setStyleSheet(
            "color: #FC8181; font-size: 16px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        af.addWidget(a_val)
        a_key = QLabel("ALERTS/HR")
        a_key.setStyleSheet(
            "color: #718096; font-size: 10px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        af.addWidget(a_key)
        cards_row.addWidget(alerts_frame)

        layout.addLayout(cards_row)

        # Divider + label
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #2D3748; border: none;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        feed_lbl = QLabel("Recent Alerts")
        feed_lbl.setStyleSheet(
            "color: #718096; font-size: 10px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        layout.addWidget(feed_lbl)

        # Scrollable recent alerts
        scroll = _make_scroll()
        self._overview_feed_container = QWidget()
        self._overview_feed_container.setStyleSheet("background: transparent;")
        self._overview_feed_layout = QVBoxLayout(self._overview_feed_container)
        self._overview_feed_layout.setContentsMargins(0, 0, 0, 0)
        self._overview_feed_layout.setSpacing(1)
        self._overview_feed_layout.addStretch()
        scroll.setWidget(self._overview_feed_container)
        layout.addWidget(scroll)

        return w

    # ------------------------------------------------------------------
    # View 1 — Alerts (filterable)
    # ------------------------------------------------------------------

    def _build_alerts(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Severity filter chips
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        self._filter_btns: list[QPushButton] = []
        chip_defs = [("ALL", None), ("🔴", "critical"), ("🟠", "high"), ("🟡", "medium"), ("⚪", "low")]
        for label, value in chip_defs:
            btn = QPushButton(label)
            active = value is None
            btn.setStyleSheet(self._chip_style(active))
            v = value
            btn.clicked.connect(lambda _checked, fv=v: self._apply_filter(fv))
            filter_row.addWidget(btn)
            self._filter_btns.append(btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        scroll = _make_scroll()
        self._alerts_container = QWidget()
        self._alerts_container.setStyleSheet("background: transparent;")
        self._alerts_layout = QVBoxLayout(self._alerts_container)
        self._alerts_layout.setContentsMargins(0, 0, 0, 0)
        self._alerts_layout.setSpacing(1)
        self._alerts_layout.addStretch()
        scroll.setWidget(self._alerts_container)
        layout.addWidget(scroll)

        return w

    @staticmethod
    def _chip_style(active: bool) -> str:
        return (
            f"QPushButton {{ color: {'#E2E8F0' if active else '#718096'}; "
            f"background-color: {'#2D3748' if active else 'transparent'}; "
            f"border: 1px solid {'#4A5568' if active else '#2D3748'}; "
            f"border-radius: 10px; padding: 2px 8px; font-size: 10px; font-family: 'Segoe UI'; }}"
            f"QPushButton:hover {{ color: #A0AEC0; border-color: #4A5568; }}"
        )

    def _apply_filter(self, severity: str | None) -> None:
        self._active_filter = severity
        values = [None, "critical", "high", "medium", "low"]
        for i, btn in enumerate(self._filter_btns):
            btn.setStyleSheet(self._chip_style(values[i] == severity))
        self._rebuild_alerts_list()

    def _rebuild_alerts_list(self) -> None:
        _clear_layout(self._alerts_layout)
        alerts = _MOCK_ALERTS if not self._active_filter else [
            a for a in _MOCK_ALERTS if a.get("severity") == self._active_filter
        ]
        for alert in sorted(alerts, key=lambda a: _SEVERITY_PRIORITY.get(a.get("severity", "low"), 4)):
            self._alerts_layout.insertWidget(self._alerts_layout.count() - 1, _AlertFeedItem(alert))
            self._alerts_layout.insertWidget(self._alerts_layout.count() - 1, _make_sep())

    # ------------------------------------------------------------------
    # View 2 — Rules
    # ------------------------------------------------------------------

    def _build_rules(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        reload_btn = QPushButton("🔄  Reload Rules")
        reload_btn.setFixedHeight(28)
        reload_btn.setStyleSheet(
            "QPushButton { color: #63B3ED; background: transparent; "
            "border: 1px solid #63B3ED55; border-radius: 6px; "
            "padding: 4px 10px; font-size: 11px; font-family: 'Segoe UI'; }"
            "QPushButton:hover { background-color: #1E2D3D; }"
        )
        layout.addWidget(reload_btn)

        scroll = _make_scroll()
        rules_container = QWidget()
        rules_container.setStyleSheet("background: transparent;")
        rules_layout = QVBoxLayout(rules_container)
        rules_layout.setContentsMargins(0, 0, 0, 0)
        rules_layout.setSpacing(2)

        for rule in _MOCK_RULES:
            rules_layout.addWidget(self._build_rule_row(rule))

        rules_layout.addStretch()
        scroll.setWidget(rules_container)
        layout.addWidget(scroll)
        return w

    def _build_rule_row(self, rule: dict) -> QFrame:
        severity = rule.get("severity", "low")
        accent = _SEVERITY_COLORS.get(severity, "#A0AEC0")
        enabled = self._rule_states.get(rule["id"], rule.get("enabled", True))

        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: #1E2330; border: none; "
            f"border-left: 3px solid {'#68D391' if enabled else '#4A5568'}; }}"
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Top row
        top = QHBoxLayout()
        id_lbl = QLabel(rule["id"])
        id_lbl.setFixedWidth(36)
        id_lbl.setStyleSheet(
            f"color: {accent}; font-size: 10px; font-weight: bold; "
            f"font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        top.addWidget(id_lbl)

        name_lbl = QLabel(rule["name"])
        name_lbl.setStyleSheet(
            "color: #E2E8F0; font-size: 11px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top.addWidget(name_lbl)

        toggle_btn = QPushButton("✓ ON" if enabled else "✗ OFF")
        toggle_btn.setFixedSize(52, 20)
        toggle_btn.setStyleSheet(self._toggle_btn_style(enabled))
        rule_id = rule["id"]
        toggle_btn.clicked.connect(lambda _ch, rid=rule_id, f=frame, b=toggle_btn: self._toggle_rule(rid, f, b))
        top.addWidget(toggle_btn)
        layout.addLayout(top)

        # Meta row
        meta_parts = [rule.get("source", ""), rule.get("mitre_id", ""), rule.get("mitre_name", "")]
        if rule.get("has_window"):
            meta_parts.append("⏱ window")
        meta_lbl = QLabel("  ·  ".join(p for p in meta_parts if p))
        meta_lbl.setStyleSheet(
            "color: #4A5568; font-size: 9px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        meta_layout = QHBoxLayout()
        meta_layout.setContentsMargins(36, 0, 0, 0)
        meta_layout.addWidget(meta_lbl)
        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        return frame

    @staticmethod
    def _toggle_btn_style(enabled: bool) -> str:
        color = "#68D391" if enabled else "#FC8181"
        return (
            f"QPushButton {{ color: {color}; background: transparent; "
            f"border: 1px solid {color}55; border-radius: 4px; "
            f"font-size: 9px; font-family: 'Segoe UI'; }}"
            f"QPushButton:hover {{ background-color: #1A1D24; }}"
        )

    def _toggle_rule(self, rule_id: str, frame: QFrame, btn: QPushButton) -> None:
        new_state = not self._rule_states.get(rule_id, True)
        self._rule_states[rule_id] = new_state
        btn.setText("✓ ON" if new_state else "✗ OFF")
        btn.setStyleSheet(self._toggle_btn_style(new_state))
        frame.setStyleSheet(
            f"QFrame {{ background-color: #1E2330; border: none; "
            f"border-left: 3px solid {'#68D391' if new_state else '#4A5568'}; }}"
        )

    # ------------------------------------------------------------------
    # View 3 — Coverage
    # ------------------------------------------------------------------

    def _build_coverage(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = _make_scroll()
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(8)

        # NIST CSF section
        csf_hdr = QLabel("NIST CSF Coverage")
        csf_hdr.setStyleSheet(
            "color: #A0AEC0; font-size: 11px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        inner_layout.addWidget(csf_hdr)
        for entry in _MOCK_CSF:
            inner_layout.addWidget(self._build_csf_row(entry))

        inner_layout.addWidget(_make_sep())

        # MITRE ATT&CK section
        mitre_hdr = QLabel("MITRE ATT&CK Coverage")
        mitre_hdr.setStyleSheet(
            "color: #A0AEC0; font-size: 11px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        inner_layout.addWidget(mitre_hdr)
        for entry in _MOCK_MITRE:
            inner_layout.addWidget(self._build_mitre_row(entry))

        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return w

    def _build_csf_row(self, entry: dict) -> QFrame:
        status = entry.get("status", "missing")
        color = _CSF_STATUS_COLORS.get(status, "#A0AEC0")
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: #1E2330; border: none; "
            f"border-left: 3px solid {color}; margin-bottom: 1px; }}"
        )
        fl = QHBoxLayout(frame)
        fl.setContentsMargins(8, 5, 8, 5)
        fl.setSpacing(8)

        fn_lbl = QLabel(entry["function"])
        fn_lbl.setFixedWidth(60)
        fn_lbl.setStyleSheet(
            "color: #E2E8F0; font-size: 11px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        fl.addWidget(fn_lbl)

        st_lbl = QLabel(status.upper())
        st_lbl.setFixedWidth(52)
        st_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        st_lbl.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: bold; "
            f"border: 1px solid {color}44; border-radius: 4px; padding: 1px 4px; background: transparent;"
        )
        fl.addWidget(st_lbl)

        cov_lbl = QLabel(entry.get("coverage", "—"))
        cov_lbl.setStyleSheet(
            "color: #718096; font-size: 10px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        cov_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        fl.addWidget(cov_lbl)

        alerts_val = entry.get("alerts", 0)
        a_lbl = QLabel(str(alerts_val) if alerts_val else "—")
        a_lbl.setFixedWidth(24)
        a_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        a_lbl.setStyleSheet(
            f"color: {'#FC8181' if alerts_val else '#4A5568'}; "
            f"font-size: 10px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        fl.addWidget(a_lbl)
        return frame

    def _build_mitre_row(self, entry: dict) -> QFrame:
        alerts_val = entry.get("alerts", 0)
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: #1E2330; border: none; "
            f"border-left: 3px solid {'#FC8181' if alerts_val else '#4A5568'}; margin-bottom: 1px; }}"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(8, 5, 8, 5)
        fl.setSpacing(2)

        top = QHBoxLayout()
        id_lbl = QLabel(entry["id"])
        id_lbl.setFixedWidth(42)
        id_lbl.setStyleSheet(
            "color: #63B3ED; font-size: 10px; font-weight: bold; "
            "font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        top.addWidget(id_lbl)

        name_lbl = QLabel(entry["name"])
        name_lbl.setStyleSheet(
            "color: #E2E8F0; font-size: 11px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top.addWidget(name_lbl)

        a_lbl = QLabel(f"{alerts_val}" if alerts_val else "0")
        a_lbl.setStyleSheet(
            f"color: {'#FC8181' if alerts_val else '#4A5568'}; "
            f"font-size: 10px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        top.addWidget(a_lbl)
        fl.addLayout(top)

        meta_lbl = QLabel(f"Tactic: {entry['tactic']}  ·  Rules: {entry['rules']}")
        meta_lbl.setStyleSheet(
            "color: #4A5568; font-size: 9px; font-family: 'Segoe UI'; border: none; background: transparent;"
        )
        fl.addWidget(meta_lbl)
        return frame

    # ------------------------------------------------------------------
    # Daemon Start / Stop (security mode only)
    # ------------------------------------------------------------------

    def _toggle_daemon(self) -> None:
        self._daemon_running = not self._daemon_running
        if self._daemon_running:
            self.daemon.start()
            self._daemon_val_lbl.setText("Running")
            self._daemon_val_lbl.setStyleSheet(
                "color: #68D391; font-size: 16px; font-weight: bold; "
                "font-family: 'Segoe UI'; border: none; background: transparent;"
            )
            self._daemon_toggle_btn.setText("⏹ Stop")
            self._daemon_toggle_btn.setStyleSheet(
                "QPushButton { color: #FC8181; background: transparent; "
                "border: 1px solid #FC818155; border-radius: 4px; "
                "font-size: 10px; padding: 2px 6px; font-family: 'Segoe UI'; }"
                "QPushButton:hover { background-color: #3D1515; }"
            )
        else:
            self.daemon.stop()
            self._daemon_val_lbl.setText("Stopped")
            self._daemon_val_lbl.setStyleSheet(
                "color: #FC8181; font-size: 16px; font-weight: bold; "
                "font-family: 'Segoe UI'; border: none; background: transparent;"
            )
            self._daemon_toggle_btn.setText("▶ Start")
            self._daemon_toggle_btn.setStyleSheet(
                "QPushButton { color: #68D391; background: transparent; "
                "border: 1px solid #68D39155; border-radius: 4px; "
                "font-size: 10px; padding: 2px 6px; font-family: 'Segoe UI'; }"
                "QPushButton:hover { background-color: #153D1D; }"
            )

    # ------------------------------------------------------------------
    # Monitoring lifecycle
    # ------------------------------------------------------------------

    def start_monitoring(self) -> None:
        """Called when entering security mode.  Daemon is already running."""
        self._switch_view(0)
        self.refresh()
        self._refresh_timer.start()
        self._notification_timer.start()

    def stop_monitoring(self) -> None:
        """Called when exiting security mode."""
        self._refresh_timer.stop()
        self._notification_timer.stop()
        self._notif_banner.hide()

    def _load_alerts(self) -> list[dict]:
        import json
        from security_daemon import ALERTS_JSONL
        alerts = []
        if ALERTS_JSONL.exists():
            try:
                with open(ALERTS_JSONL, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            alerts.append(json.loads(line.strip()))
            except Exception:
                pass
        if not alerts:
            # Fallback to keep UI interesting when empty
            return _MOCK_ALERTS
        return alerts

    def refresh(self) -> None:
        """Rebuild overview feed and alerts list from current data."""
        self._rebuild_overview_feed()
        self._rebuild_alerts_list()
        self._check_new_alerts()

    def _rebuild_overview_feed(self) -> None:
        _clear_layout(self._overview_feed_layout)
        alerts = sorted(self._load_alerts(), key=lambda a: _SEVERITY_PRIORITY.get(a.get("severity", "low"), 4))[:4]
        for alert in alerts:
            self._overview_feed_layout.insertWidget(
                self._overview_feed_layout.count() - 1, _AlertFeedItem(alert, compact=True)
            )
            self._overview_feed_layout.insertWidget(self._overview_feed_layout.count() - 1, _make_sep())

    def _check_new_alerts(self) -> None:
        """
        Emit alert_triggered for the first unnotified critical alert.
        """
        for alert in self._load_alerts():
            if alert.get("severity") == "critical" and alert["id"] not in self._notified_ids:
                self._notified_ids.add(alert["id"])
                self._notif_label.setText(f"🚨 {alert['title']}  ({alert.get('host', '')})")
                self._notif_banner.show()
                self.alert_triggered.emit(alert["severity"], alert["title"])
                break  # one notification at a time to avoid spam


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _make_scroll() -> QScrollArea:
    """Return a pre-styled frameless scroll area."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet(
        "QScrollArea { border: none; background-color: transparent; }"
        "QScrollBar:vertical { border: none; background: #1A1D24; width: 6px; }"
        "QScrollBar::handle:vertical { background: #4A5568; border-radius: 3px; }"
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
    )
    return scroll


def _make_sep() -> QFrame:
    """Return a 1-px dark horizontal separator."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("background-color: #2D3748; border: none;")
    sep.setFixedHeight(1)
    return sep


def _clear_layout(layout) -> None:
    """Remove all widgets from layout except the trailing stretch."""
    while layout.count() > 1:
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
