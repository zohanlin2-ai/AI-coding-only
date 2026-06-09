"""
network_packet_monitor.py — Advanced Network Packet Monitor UI for Ann.

Follows the layout and features specified in network-packet-monitor-ui-spec.md.
"""
from __future__ import annotations

import random
import time
import json
import logging
import platform
import subprocess
from datetime import datetime
from queue import Queue

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
        QScrollArea, QSizePolicy, QPushButton, QLineEdit, QComboBox,
        QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
        QTextEdit, QSplitter,
    )
    from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QColor
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
        QScrollArea, QSizePolicy, QPushButton, QLineEdit, QComboBox,
        QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
        QTextEdit, QSplitter,
    )
    from PySide6.QtCore import Qt, QTimer, QThread, Signal
    from PySide6.QtGui import QFont, QColor
    pyqtSignal = Signal

logger = logging.getLogger(__name__)

# Color Palette (Semantic Tokens consistent with Ann's design system)
_COLORS = {
    "bg_dark":      "#1A1D24",
    "bg_card":      "#1E2330",
    "border":       "#2D3748",
    "border_hover": "#4A5568",
    "text_main":     "#E2E8F0",
    "text_muted":    "#718096",
    "text_dark":     "#4A5568",
    
    # Semantic States
    "info":         "#63B3ED",  # TCP / TLS (Blue)
    "success":      "#68D391",  # UDP / Running (Green)
    "warning":      "#ECC94B",  # DNS / Paused (Yellow)
    "danger":       "#E53E3E",  # Suspicious / Critical Alert (Red)
    "secondary":    "#A0AEC0",  # HTTP / Neutral (Gray)
}

# Suspicious indicators matching the spec
SUSPICIOUS_IPS = [
    "185.220.101.47",
    "23.95.110.24",
    "91.108.4.1",
    "104.21.66.213",
]

SUSPICIOUS_PORTS = [4444, 1337, 31337, 6667, 12345]

SUSPICIOUS_DNS = [
    "xn--malw4r3.cc",
    "update.malicious-domain.tk",
    "c2-server.xyz",
    "dynamic-dns.nip.io",
]

MOCK_INTERFACES = ["eth0", "wlan0", "lo", "Ethernet 1"]

# Mock data generation pools
IP_POOL = [
    "192.168.1.15", "192.168.1.102", "10.0.0.5", "10.0.0.12",
    "8.8.8.8", "1.1.1.1", "142.250.190.46", "185.220.101.47",
    "23.95.110.24", "91.108.4.1", "104.21.66.213"
]

DOMAINS = [
    "google.com", "github.com", "microsoft.com", "update.ann-assistant.io",
    "xn--malw4r3.cc", "c2-server.xyz", "wikipedia.org", "yahoo.com"
]


class PacketEvent:
    def __init__(
        self,
        seq: int,
        src: str,
        dst: str,
        sport: int,
        dport: int,
        proto: str,
        length: int,
        summary: str,
        payload: str,
        mitre: str | None = None,
        is_suspicious: bool = False
    ):
        self.seq = seq
        self.time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.src = src
        self.dst = dst
        self.sport = sport
        self.dport = dport
        self.proto = proto
        self.length = length
        self.summary = summary
        self.payload = payload
        self.mitre = mitre
        self.is_suspicious = is_suspicious


class RealConnectionGenerator(QThread):
    """Monitors real active host TCP connections and streams them to the UI."""
    packet_received = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._running = True
        self._paused = False
        self.seq_counter = 1
        self.seen_connections: set[tuple[str, int, str, int]] = set()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._running = False
        self.wait()

    def run(self) -> None:
        # Populate initial connections so we only capture new ones
        self.seen_connections = self._get_active_connections()
        
        while self._running:
            if self._paused:
                self.msleep(200)
                continue

            try:
                current_conns = self._get_active_connections()
                new_conns = current_conns - self.seen_connections
                for conn in new_conns:
                    local_ip, local_port, remote_ip, remote_port = conn
                    
                    is_suspicious = (
                        remote_ip in SUSPICIOUS_IPS or
                        remote_port in SUSPICIOUS_PORTS
                    )
                    
                    proto = "SUSPICIOUS" if is_suspicious else "TCP"
                    mitre_id = None
                    if is_suspicious:
                        if remote_port in SUSPICIOUS_PORTS:
                            mitre_id = "T1571 - Non-Standard Port"
                        else:
                            mitre_id = "T1071.001 - Web Protocols"
                    
                    summary = f"ESTABLISHED: {local_ip}:{local_port} -> {remote_ip}:{remote_port}"
                    if is_suspicious:
                        summary = f"C2 SUSPICIOUS: {local_ip}:{local_port} -> {remote_ip}:{remote_port}"

                    payload = (
                        f"Active TCP Connection Event\n"
                        f"State: ESTABLISHED\n"
                        f"Local: {local_ip}:{local_port}\n"
                        f"Remote: {remote_ip}:{remote_port}\n"
                        f"Alert: {'Suspicious connection detected' if is_suspicious else 'Normal system traffic'}"
                    )

                    pkt = PacketEvent(
                        seq=self.seq_counter,
                        src=local_ip,
                        dst=remote_ip,
                        sport=local_port,
                        dport=remote_port,
                        proto=proto,
                        length=random.randint(64, 1500) if not is_suspicious else random.randint(150, 800),
                        summary=summary,
                        payload=payload,
                        mitre=mitre_id,
                        is_suspicious=is_suspicious
                    )
                    self.packet_received.emit(pkt)
                    self.seq_counter += 1

                self.seen_connections = current_conns
            except Exception as e:
                logger.error("Error in RealConnectionGenerator: %s", e)

            self.msleep(3000)

    def _get_active_connections(self) -> set[tuple[str, int, str, int]]:
        conns = set()
        system = platform.system()
        if system == "Windows":
            try:
                # Use powershell to list connections
                cmd = ["powershell", "-NoProfile", "-Command",
                       "Get-NetTCPConnection | Where-Object { $_.State -eq 'Established' } | Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort | ConvertTo-Json"]
                res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=10)
                if res.returncode == 0 and res.stdout.strip():
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        local_ip = item.get("LocalAddress")
                        local_port = item.get("LocalPort")
                        remote_ip = item.get("RemoteAddress")
                        remote_port = item.get("RemotePort")
                        if local_ip and local_port and remote_ip and remote_port:
                            conns.add((str(local_ip), int(local_port), str(remote_ip), int(remote_port)))
            except Exception as e:
                logger.debug("Failed to list Windows connections: %s", e)
        else:
            # macOS / Linux: use netstat -an
            try:
                cmd = ["netstat", "-an"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        if "ESTABLISHED" in line:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                local_part = parts[3]
                                remote_part = parts[4]
                                
                                def parse_addr(addr_str: str) -> tuple[str, int]:
                                    if "." in addr_str and addr_str.count(".") >= 4:
                                        ip_parts = addr_str.split(".")
                                        ip = ".".join(ip_parts[:-1])
                                        port = int(ip_parts[-1])
                                        return ip, port
                                    elif ":" in addr_str:
                                        ip_parts = addr_str.rsplit(":", 1)
                                        return ip_parts[0], int(ip_parts[1])
                                    return addr_str, 0
                                
                                try:
                                    lip, lport = parse_addr(local_part)
                                    rip, rport = parse_addr(remote_part)
                                    if lip and lport and rip and rport:
                                        conns.add((lip, lport, rip, rport))
                                except Exception:
                                    continue
            except Exception as e:
                logger.debug("Failed to list Unix connections: %s", e)
        return conns


class NetworkPacketMonitorWindow(QWidget):
    """Compact packet console UI conforming to network-packet-monitor-ui-spec.md"""

    def __init__(self, config: dict = None, parent=None):
        super().__init__(parent)
        self.config = config or {}
        self.setWindowTitle("🌐 Network Packet Monitor Console")
        self.resize(1000, 650)
        self.setStyleSheet(f"background-color: {_COLORS['bg_dark']};")

        # Core State
        self.packets_history: list[PacketEvent] = []
        self.filtered_packets: list[PacketEvent] = []
        self.current_filter_expr = ""
        self.captured_count = 0
        self.suspicious_count = 0
        self.alert_count = 0
        self.total_bytes = 0
        self.active_connections: set[tuple[str, int, str, int]] = set()
        
        # Timing stats
        self.packets_last_sec = 0
        self.current_packets_per_sec = 0

        # Build Subcomponents
        self._setup_ui()

        # Start packet generator thread
        self.generator = RealConnectionGenerator()
        self.generator.packet_received.connect(self._handle_new_packet)
        self.generator.start()

        # Start 1s Stats timer
        self.stats_timer = QTimer(self)
        self.stats_timer.setInterval(1000)
        self.stats_timer.timeout.connect(self._update_sec_stats)
        self.stats_timer.start()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Toolbar
        layout.addWidget(self._build_toolbar())

        # 2. Stats Bar
        layout.addWidget(self._build_stats_bar())

        # 3. Main Area Splitter (Table + Detail)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setStyleSheet("QSplitter::handle { background-color: #2D3748; }")
        
        # Packet Table Container
        table_container = QWidget()
        tc_layout = QVBoxLayout(table_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        self.packet_table = QTableWidget(0, 7)
        self.packet_table.setHorizontalHeaderLabels(["#", "Time", "Source", "Destination", "Protocol", "Length", "Summary"])
        self.packet_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.packet_table.horizontalHeader().setStretchLastSection(True)
        self.packet_table.verticalHeader().setVisible(False)
        self.packet_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.packet_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.packet_table.setFont(QFont("Consolas", 9))
        self.packet_table.setStyleSheet(
            f"QTableWidget {{ background-color: {_COLORS['bg_card']}; color: {_COLORS['text_main']}; "
            f"border: 1px solid {_COLORS['border']}; gridline-color: {_COLORS['border']}; }}"
            f"QHeaderView::section {{ background-color: {_COLORS['bg_dark']}; color: {_COLORS['text_muted']}; "
            f"padding: 4px; border: 1px solid {_COLORS['border']}; font-weight: bold; }}"
        )
        self.packet_table.itemSelectionChanged.connect(self._handle_row_selection)
        tc_layout.addWidget(self.packet_table)
        main_splitter.addWidget(table_container)

        # Detail Pane
        self.detail_pane = self._build_detail_pane()
        main_splitter.addWidget(self.detail_pane)
        main_splitter.setSizes([650, 350])
        
        layout.addWidget(main_splitter, stretch=2)

        # 4. Bottom Tab Panel (Alerts | DNS | Connections)
        layout.addWidget(self._build_bottom_tabs(), stretch=1)

        # 5. Status Bar
        layout.addWidget(self._build_status_bar())

    def _build_toolbar(self) -> QWidget:
        tb = QFrame()
        tb.setStyleSheet(f"QFrame {{ background-color: {_COLORS['bg_card']}; border: 1px solid {_COLORS['border']}; border-radius: 6px; }}")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(6, 4, 6, 4)
        tbl.setSpacing(8)

        # Filter Input
        lbl_filter = QLabel("Filter:")
        lbl_filter.setStyleSheet(f"color: {_COLORS['text_muted']}; border: none; font-weight: bold;")
        tbl.addWidget(lbl_filter)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("e.g. proto == DNS or suspicious == true")
        self.txt_filter.setStyleSheet(
            f"QLineEdit {{ background-color: {_COLORS['bg_dark']}; color: {_COLORS['text_main']}; "
            f"border: 1px solid {_COLORS['border']}; border-radius: 4px; padding: 3px 8px; font-family: 'Consolas'; }}"
        )
        self.txt_filter.returnPressed.connect(self._apply_filter)
        tbl.addWidget(self.txt_filter, stretch=2)

        # Apply Filter Button
        btn_apply = QPushButton("Apply")
        btn_apply.setStyleSheet(
            f"QPushButton {{ color: {_COLORS['info']}; border: 1px solid {_COLORS['info']}55; "
            f"border-radius: 4px; padding: 3px 10px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {_COLORS['info']}22; }}"
        )
        btn_apply.clicked.connect(self._apply_filter)
        tbl.addWidget(btn_apply)

        # Play / Pause Button
        self.btn_capture = QPushButton("⏸ Pause")
        self.btn_capture.setStyleSheet(
            f"QPushButton {{ color: {_COLORS['success']}; border: 1px solid {_COLORS['success']}55; "
            f"border-radius: 4px; padding: 3px 10px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {_COLORS['success']}22; }}"
        )
        self.btn_capture.clicked.connect(self._toggle_capture)
        tbl.addWidget(self.btn_capture)

        # Clear Button
        btn_clear = QPushButton("🗑 Clear")
        btn_clear.setStyleSheet(
            f"QPushButton {{ color: {_COLORS['danger']}; border: 1px solid {_COLORS['danger']}55; "
            f"border-radius: 4px; padding: 3px 10px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {_COLORS['danger']}22; }}"
        )
        btn_clear.clicked.connect(self._clear_all)
        tbl.addWidget(btn_clear)

        # Interface Selector
        lbl_iface = QLabel("Iface:")
        lbl_iface.setStyleSheet(f"color: {_COLORS['text_muted']}; border: none; font-weight: bold;")
        tbl.addWidget(lbl_iface)

        self.cb_interface = QComboBox()
        self.cb_interface.addItems(MOCK_INTERFACES)
        self.cb_interface.setStyleSheet(
            f"QComboBox {{ background-color: {_COLORS['bg_dark']}; color: {_COLORS['text_main']}; "
            f"border: 1px solid {_COLORS['border']}; border-radius: 4px; padding: 2px 6px; }}"
        )
        self.cb_interface.currentTextChanged.connect(self._handle_interface_change)
        tbl.addWidget(self.cb_interface)

        # Total Packet Counter
        self.lbl_total_counter = QLabel("Packets: 0")
        self.lbl_total_counter.setStyleSheet(f"color: {_COLORS['text_main']}; font-weight: bold; border: none; padding-left: 6px;")
        tbl.addWidget(self.lbl_total_counter)

        # Close Button
        btn_close = QPushButton("✕ Close")
        btn_close.setStyleSheet(
            f"QPushButton {{ color: {_COLORS['danger']}; background: transparent; border: 1px solid {_COLORS['danger']}55; "
            f"border-radius: 4px; padding: 3px 10px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: #3D1515; }}"
        )
        btn_close.clicked.connect(self.close)
        tbl.addWidget(btn_close)

        return tb

    def _build_stats_bar(self) -> QWidget:
        sb = QWidget()
        sbl = QHBoxLayout(sb)
        sbl.setContentsMargins(0, 0, 0, 0)
        sbl.setSpacing(6)

        # Stat cards definitions
        self.stat_cards = {}
        metrics = [
            ("Packets/sec", "0", "info"),
            ("Total Bytes", "0 B", "success"),
            ("Active Conns", "0", "secondary"),
            ("Suspicious Packets", "0", "warning"),
            ("Alerts", "0", "danger")
        ]

        for title, val, color_key in metrics:
            frame = QFrame()
            frame.setStyleSheet(
                f"QFrame {{ background-color: {_COLORS['bg_card']}; border: 1px solid {_COLORS['border']}; "
                f"border-left: 4px solid {_COLORS[color_key]}; border-radius: 6px; }}"
            )
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(8, 6, 8, 6)
            fl.setSpacing(1)

            val_lbl = QLabel(val)
            val_lbl.setStyleSheet(f"color: {_COLORS[color_key]}; font-size: 16px; font-weight: bold; font-family: 'Consolas'; border: none;")
            fl.addWidget(val_lbl)

            title_lbl = QLabel(title.upper())
            title_lbl.setStyleSheet(f"color: {_COLORS['text_muted']}; font-size: 9px; font-weight: bold; border: none;")
            fl.addWidget(title_lbl)

            sbl.addWidget(frame)
            self.stat_cards[title] = val_lbl

        return sb

    def _build_detail_pane(self) -> QWidget:
        dp = QFrame()
        dp.setMinimumWidth(320)
        dp.setStyleSheet(f"QFrame {{ background-color: {_COLORS['bg_card']}; border: 1px solid {_COLORS['border']}; border-radius: 6px; }}")
        dpl = QVBoxLayout(dp)
        dpl.setContentsMargins(8, 8, 8, 8)
        dpl.setSpacing(6)

        hdr = QLabel("Packet Details")
        hdr.setStyleSheet(f"color: {_COLORS['info']}; font-size: 12px; font-weight: bold; border: none;")
        dpl.addWidget(hdr)

        # Monospace detail display text area
        self.txt_detail = QTextEdit()
        self.txt_detail.setReadOnly(True)
        self.txt_detail.setFont(QFont("Consolas", 9))
        self.txt_detail.setStyleSheet(
            f"QTextEdit {{ background-color: {_COLORS['bg_dark']}; color: {_COLORS['text_main']}; "
            f"border: 1px solid {_COLORS['border']}; border-radius: 4px; padding: 6px; }}"
        )
        dpl.addWidget(self.txt_detail, stretch=2)

        # AI Action button
        self.btn_ai_analysis = QPushButton("🤖 Analyze with AI")
        self.btn_ai_analysis.setEnabled(False)
        self.btn_ai_analysis.setStyleSheet(
            f"QPushButton {{ color: {_COLORS['info']}; background-color: {_COLORS['bg_dark']}; "
            f"border: 1px solid {_COLORS['info']}66; border-radius: 4px; padding: 4px 10px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {_COLORS['info']}22; }}"
            f"QPushButton:disabled {{ color: {_COLORS['text_dark']}; border-color: {_COLORS['border']}; }}"
        )
        self.btn_ai_analysis.clicked.connect(self._run_ai_analysis)
        dpl.addWidget(self.btn_ai_analysis)

        return dp

    def _build_bottom_tabs(self) -> QWidget:
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"QTabWidget::panel {{ border: 1px solid {_COLORS['border']}; background-color: {_COLORS['bg_card']}; border-radius: 4px; }}"
            f"QTabBar::tab {{ background-color: {_COLORS['bg_dark']}; color: {_COLORS['text_muted']}; "
            f"padding: 4px 12px; border: 1px solid {_COLORS['border']}; border-bottom-color: transparent; "
            f"border-top-left-radius: 4px; border-top-right-radius: 4px; font-size: 10px; font-weight: bold; }}"
            f"QTabBar::tab:selected {{ background-color: {_COLORS['bg_card']}; color: {_COLORS['text_main']}; border-color: {_COLORS['border']}; }}"
        )

        # Tab 1: Alerts log
        self.alerts_log = QTextEdit()
        self.alerts_log.setReadOnly(True)
        self.alerts_log.setFont(QFont("Consolas", 9))
        self.alerts_log.setStyleSheet(f"background-color: {_COLORS['bg_dark']}; color: {_COLORS['danger']}; border: none; padding: 4px;")
        self.tabs.addTab(self.alerts_log, "⚠️ ALERTS")

        # Tab 2: DNS queries
        self.dns_log = QTextEdit()
        self.dns_log.setReadOnly(True)
        self.dns_log.setFont(QFont("Consolas", 9))
        self.dns_log.setStyleSheet(f"background-color: {_COLORS['bg_dark']}; color: {_COLORS['warning']}; border: none; padding: 4px;")
        self.tabs.addTab(self.dns_log, "🔍 DNS QUERIES")

        # Tab 3: Active Connections
        self.connections_log = QTextEdit()
        self.connections_log.setReadOnly(True)
        self.connections_log.setFont(QFont("Consolas", 9))
        self.connections_log.setStyleSheet(f"background-color: {_COLORS['bg_dark']}; color: {_COLORS['info']}; border: none; padding: 4px;")
        self.tabs.addTab(self.connections_log, "🔗 CONNECTIONS")

        return self.tabs

    def _build_status_bar(self) -> QWidget:
        sb = QFrame()
        sb.setStyleSheet(f"QFrame {{ background-color: {_COLORS['bg_card']}; border-top: 1px solid {_COLORS['border']}; }}")
        sbl = QHBoxLayout(sb)
        sbl.setContentsMargins(6, 2, 6, 2)

        self.lbl_status_state = QLabel("● RUNNING")
        self.lbl_status_state.setStyleSheet(f"color: {_COLORS['success']}; font-weight: bold; border: none; font-size: 10px;")
        sbl.addWidget(self.lbl_status_state)

        self.lbl_status_iface = QLabel(f"Iface: {MOCK_INTERFACES[0]}")
        self.lbl_status_iface.setStyleSheet(f"color: {_COLORS['text_muted']}; border: none; font-size: 10px;")
        sbl.addWidget(self.lbl_status_iface)

        self.lbl_status_queue = QLabel("Queue: 0")
        self.lbl_status_queue.setStyleSheet(f"color: {_COLORS['text_muted']}; border: none; font-size: 10px;")
        sbl.addWidget(self.lbl_status_queue)

        self.lbl_status_drops = QLabel("Drops: 0")
        self.lbl_status_drops.setStyleSheet(f"color: {_COLORS['text_muted']}; border: none; font-size: 10px;")
        sbl.addWidget(self.lbl_status_drops)

        sbl.addStretch()

        self.lbl_status_time = QLabel("")
        self.lbl_status_time.setStyleSheet(f"color: {_COLORS['text_muted']}; border: none; font-family: 'Consolas'; font-size: 10px;")
        sbl.addWidget(self.lbl_status_time)

        return sb

    # ------------------------------------------------------------------
    # Data Processing and UI Updates
    # ------------------------------------------------------------------

    def _handle_new_packet(self, pkt: PacketEvent) -> None:
        self.captured_count += 1
        self.packets_last_sec += 1
        self.total_bytes += pkt.length
        
        # Add to connection tracking
        conn = (pkt.src, pkt.sport, pkt.dst, pkt.dport)
        self.active_connections.add(conn)

        # Update lists
        self.packets_history.append(pkt)
        if len(self.packets_history) > 500:
            self.packets_history.pop(0)

        # Trigger filters
        matches_filter = self._eval_filter_expression(pkt, self.current_filter_expr)
        if matches_filter:
            self.filtered_packets.append(pkt)
            if len(self.filtered_packets) > 100:
                self.filtered_packets.pop(0)
            self._add_row_to_table(pkt)

        # Handle suspicious status updates
        if pkt.is_suspicious:
            self.suspicious_count += 1
            # Tab-alerts / log logging
            alert_str = f"[{pkt.time}] {pkt.mitre or 'Suspicious Traffic'} from {pkt.src}:{pkt.sport} to {pkt.dst}:{pkt.dport}\n"
            self.alerts_log.append(alert_str)
            self.alert_count += 1

        if pkt.proto == "DNS":
            dns_str = f"[{pkt.time}] {pkt.src} -> {pkt.summary.replace('Standard Query ', '')}"
            if pkt.is_suspicious:
                dns_str += " [SUSPICIOUS]"
            self.dns_log.append(dns_str + "\n")

        # Periodically refresh connection panel text
        if self.captured_count % 10 == 0:
            self._refresh_connections_panel()

        # Update stats text labels
        self.lbl_total_counter.setText(f"Packets: {self.captured_count}")
        self.stat_cards["Total Bytes"].setText(self._format_bytes(self.total_bytes))
        self.stat_cards["Active Conns"].setText(str(len(self.active_connections)))
        self.stat_cards["Suspicious Packets"].setText(str(self.suspicious_count))
        self.stat_cards["Alerts"].setText(str(self.alert_count))
        self.lbl_status_queue.setText(f"Queue: {random.randint(0, 3)}") # Simulated depth

    def _refresh_connections_panel(self) -> None:
        self.connections_log.clear()
        # Sort and show top connections
        for conn in sorted(list(self.active_connections))[-20:]:
            self.connections_log.append(f"CONN  {conn[0]}:{conn[1]} -> {conn[2]}:{conn[3]}\n")

    def _add_row_to_table(self, pkt: PacketEvent) -> None:
        # Keep table size bounded
        if self.packet_table.rowCount() >= 80:
            self.packet_table.removeRow(0)

        row = self.packet_table.rowCount()
        self.packet_table.insertRow(row)

        items = [
            str(pkt.seq),
            pkt.time,
            f"{pkt.src}:{pkt.sport}",
            f"{pkt.dst}:{pkt.dport}",
            pkt.proto,
            str(pkt.length),
            pkt.summary
        ]

        for col, val in enumerate(items):
            item = QTableWidgetItem(val)
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            
            # Styling protocol column specifically with background Badges
            if col == 4:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                color = _COLORS.get(pkt.proto.lower(), _COLORS["secondary"])
                item.setForeground(QColor("#FFFFFF"))
                item.setBackground(QColor(color))
            
            # Highlight whole row if suspicious
            if pkt.is_suspicious and col != 4:
                item.setForeground(QColor(_COLORS["danger"]))
                
            self.packet_table.setItem(row, col, item)

        # Auto-scroll if scrollbar is near the bottom
        scrollbar = self.packet_table.verticalScrollBar()
        if scrollbar.maximum() - scrollbar.value() <= 2:
            self.packet_table.scrollToBottom()

    def _eval_filter_expression(self, pkt: PacketEvent, expr: str) -> bool:
        """Simple expression parser mapping fields to attributes."""
        if not expr:
            return True

        expr = expr.strip().lower()
        
        # Exact keyword matches
        if expr in ("dns", "tcp", "udp", "tls", "http", "suspicious"):
            return pkt.proto.lower() == expr or (expr == "suspicious" and pkt.is_suspicious)

        # Simple field matching parser
        try:
            if "==" in expr:
                field, val = expr.split("==", 1)
                field = field.strip()
                val = val.strip().replace("'", "").replace('"', "")
                if field in ("ip.src", "src"):
                    return pkt.src == val
                if field in ("ip.dst", "dst"):
                    return pkt.dst == val
                if field in ("tcp.port", "udp.port", "port"):
                    return str(pkt.sport) == val or str(pkt.dport) == val
                if field in ("proto", "protocol"):
                    return pkt.proto.lower() == val
                if field == "suspicious":
                    return str(pkt.is_suspicious).lower() == val
            elif "contains" in expr:
                field, val = expr.split("contains", 1)
                field = field.strip()
                val = val.strip().replace("'", "").replace('"', "")
                if field == "mitre":
                    return pkt.mitre is not None and val in pkt.mitre.lower()
        except Exception:
            pass

        # String fallback search
        return (
            expr in pkt.src.lower() or
            expr in pkt.dst.lower() or
            expr in pkt.proto.lower() or
            expr in pkt.summary.lower()
        )

    def _handle_row_selection(self) -> None:
        selected_rows = self.packet_table.selectionModel().selectedRows()
        if not selected_rows:
            self.txt_detail.clear()
            self.btn_ai_analysis.setEnabled(False)
            return

        row_index = selected_rows[0].row()
        seq_item = self.packet_table.item(row_index, 0)
        if not seq_item:
            return

        seq = int(seq_item.text())
        pkt = next((p for p in self.packets_history if p.seq == seq), None)
        if not pkt:
            return

        # Render detail pane text block
        detail_text = (
            f"=== Packet Details ===\n"
            f"Sequence No. : #{pkt.seq}\n"
            f"Arrival Time : {pkt.time}\n"
            f"Protocol     : {pkt.proto}\n"
            f"Length       : {pkt.length} bytes\n\n"
            f"=== Network Headers ===\n"
            f"Source IP    : {pkt.src}:{pkt.sport}\n"
            f"Dest IP      : {pkt.dst}:{pkt.dport}\n"
            f"TTL Value    : {random.randint(64, 128)}\n\n"
        )
        if pkt.mitre:
            detail_text += (
                f"=== MITRE ATT&CK Mapping ===\n"
                f"Technique    : {pkt.mitre}\n\n"
            )
        detail_text += (
            f"=== Text Payload Payload ===\n"
            f"{pkt.payload}\n\n"
            f"=== Hex Raw Hex Dump ===\n"
            f"{self._to_hex_dump(pkt.payload)}"
        )
        
        self.txt_detail.setPlainText(detail_text)
        self.btn_ai_analysis.setEnabled(True)

    def _run_ai_analysis(self) -> None:
        selected_rows = self.packet_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row_index = selected_rows[0].row()
        seq = int(self.packet_table.item(row_index, 0).text())
        pkt = next((p for p in self.packets_history if p.seq == seq), None)
        if not pkt:
            return

        self.txt_detail.append("\n\n🤖 [AI Analysis Engine Running...]")
        self.btn_ai_analysis.setEnabled(False)

        # Worker for Ollama enrichment
        class AIAnalysisWorker(QThread):
            analysis_finished = pyqtSignal(str)
            
            def __init__(self, packet: PacketEvent, config: dict):
                super().__init__()
                self.pkt = packet
                self.config = config

            def run(self) -> None:
                from ollama_client import OllamaClient
                base_url = self.config.get("llm", {}).get("base_url", "http://localhost:11434")
                model = self.config.get("llm", {}).get("model", "gemma4:e4b")
                client = OllamaClient(base_url)
                
                prompt = (
                    f"Please analyze the following network packet payload for maliciousness:\n"
                    f"Protocol: {self.pkt.proto}\n"
                    f"Src: {self.pkt.src}:{self.pkt.sport} -> Dst: {self.pkt.dst}:{self.pkt.dport}\n"
                    f"Payload: {self.pkt.payload}\n\n"
                    f"Provide a short security assessment verdict and action plan in concise bullet points."
                )
                try:
                    res = client.chat(model, [{"role": "user", "content": prompt}])
                    self.analysis_finished.emit(res)
                except Exception as e:
                    self.analysis_finished.emit(f"AI Analysis failed: {e}")

        self.ai_worker = AIAnalysisWorker(pkt, self.config)
        self.ai_worker.analysis_finished.connect(self._handle_ai_result)
        self.ai_worker.start()

    def _handle_ai_result(self, result: str) -> None:
        self.txt_detail.append(f"\n\n=== AI Security Verdict ===\n{result}")
        self.btn_ai_analysis.setEnabled(True)

    # ------------------------------------------------------------------
    # Toolbar Interactions
    # ------------------------------------------------------------------

    def _apply_filter(self) -> None:
        self.current_filter_expr = self.txt_filter.text()
        self.packet_table.setRowCount(0)
        self.filtered_packets.clear()
        
        # Re-apply filters to existing history list
        for pkt in self.packets_history:
            if self._eval_filter_expression(pkt, self.current_filter_expr):
                self.filtered_packets.append(pkt)
                self._add_row_to_table(pkt)

    def _toggle_capture(self) -> None:
        if self.generator._paused:
            self.generator.resume()
            self.btn_capture.setText("⏸ Pause")
            self.btn_capture.setStyleSheet(
                f"QPushButton {{ color: {_COLORS['success']}; border: 1px solid {_COLORS['success']}55; "
                f"border-radius: 4px; padding: 3px 10px; font-weight: bold; }}"
                f"QPushButton:hover {{ background-color: {_COLORS['success']}22; }}"
            )
            self.lbl_status_state.setText("● RUNNING")
            self.lbl_status_state.setStyleSheet(f"color: {_COLORS['success']}; font-weight: bold; border: none; font-size: 10px;")
        else:
            self.generator.pause()
            self.btn_capture.setText("▶ Resume")
            self.btn_capture.setStyleSheet(
                f"QPushButton {{ color: {_COLORS['warning']}; border: 1px solid {_COLORS['warning']}55; "
                f"border-radius: 4px; padding: 3px 10px; font-weight: bold; }}"
                f"QPushButton:hover {{ background-color: {_COLORS['warning']}22; }}"
            )
            self.lbl_status_state.setText("● PAUSED")
            self.lbl_status_state.setStyleSheet(f"color: {_COLORS['warning']}; font-weight: bold; border: none; font-size: 10px;")

    def _clear_all(self) -> None:
        self.packets_history.clear()
        self.filtered_packets.clear()
        self.packet_table.setRowCount(0)
        self.active_connections.clear()
        self.total_bytes = 0
        self.suspicious_count = 0
        self.alert_count = 0
        self.captured_count = 0
        
        # Clear text widgets
        self.txt_detail.clear()
        self.alerts_log.clear()
        self.dns_log.clear()
        self.connections_log.clear()

        # Update stats displays
        self.lbl_total_counter.setText("Packets: 0")
        for k in self.stat_cards:
            self.stat_cards[k].setText("0" if k != "Total Bytes" else "0 B")

    def _handle_interface_change(self, text: str) -> None:
        self.lbl_status_iface.setText(f"Iface: {text}")

    def _update_sec_stats(self) -> None:
        # Update clock
        self.lbl_status_time.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Update packets/sec rate
        self.current_packets_per_sec = self.packets_last_sec
        self.packets_last_sec = 0
        self.stat_cards["Packets/sec"].setText(str(self.current_packets_per_sec))

    def closeEvent(self, event) -> None:
        # Clean up threads
        self.generator.stop()
        self.stats_timer.stop()
        event.accept()

    # ------------------------------------------------------------------
    # Static Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_bytes(size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @staticmethod
    def _to_hex_dump(data_str: str) -> str:
        # Generate basic hex dump lines
        bytes_arr = data_str.encode("utf-8", errors="ignore")
        lines = []
        for i in range(0, min(len(bytes_arr), 128), 16):
            chunk = bytes_arr[i:i+16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            text_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{i:04x}  {hex_part:<48}  {text_part}")
        return "\n".join(lines)
