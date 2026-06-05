import sys
import os
from queue import Queue
from pathlib import Path
import pytest

# Force offscreen rendering for GUI tests
os.environ["QT_QPA_PLATFORM"] = "offscreen"

HAS_QT = False
try:
    from PyQt6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication
        HAS_QT = True
    except ImportError:
        HAS_QT = False

pytestmark = pytest.mark.skipif(not HAS_QT, reason="PyQt6 or PySide6 is required for GUI tests")

if HAS_QT:
    app = QApplication.instance() or QApplication(sys.argv)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from network_packet_monitor import PacketEvent, RealConnectionGenerator, NetworkPacketMonitorWindow

def test_packet_event_creation():
    pkt = PacketEvent(
        seq=1,
        src="10.0.0.5",
        dst="185.220.101.47",
        sport=5000,
        dport=4444,
        proto="SUSPICIOUS",
        length=256,
        summary="C2 Connection",
        payload="powershell -enc ...",
        mitre="T1071.001",
        is_suspicious=True
    )
    assert pkt.seq == 1
    assert pkt.src == "10.0.0.5"
    assert pkt.dst == "185.220.101.47"
    assert pkt.sport == 5000
    assert pkt.dport == 4444
    assert pkt.proto == "SUSPICIOUS"
    assert pkt.length == 256
    assert pkt.summary == "C2 Connection"
    assert pkt.payload == "powershell -enc ..."
    assert pkt.mitre == "T1071.001"
    assert pkt.is_suspicious is True
    assert pkt.time is not None


def test_real_connection_generator(monkeypatch):
    generator = RealConnectionGenerator()
    
    # Mock platform and connections
    monkeypatch.setattr("platform.system", lambda: "Windows")
    
    import json
    class MockWindowsCompletedProcess:
        returncode = 0
        stdout = json.dumps([
            {
                "LocalAddress": "192.168.1.100",
                "LocalPort": 50505,
                "RemoteAddress": "8.8.8.8",
                "RemotePort": 53
            }
        ])
        
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: MockWindowsCompletedProcess())
    conns = generator._get_active_connections()
    assert len(conns) == 1
    assert ("192.168.1.100", 50505, "8.8.8.8", 53) in conns


def test_filter_matching():
    # We pass qapp fixture to ensure Qt structures are initialized if needed
    win = NetworkPacketMonitorWindow()
    
    pkt_dns = PacketEvent(
        seq=10,
        src="10.0.0.5",
        dst="8.8.8.8",
        sport=53000,
        dport=53,
        proto="DNS",
        length=80,
        summary="Standard Query A xn--malw4r3.cc",
        payload="xn--malw4r3.cc",
        mitre="T1568",
        is_suspicious=True
    )
    
    # Test simple protocols
    assert win._eval_filter_expression(pkt_dns, "dns") is True
    assert win._eval_filter_expression(pkt_dns, "tcp") is False
    
    # Test suspicious
    assert win._eval_filter_expression(pkt_dns, "suspicious") is True
    
    # Test source/destination fields
    assert win._eval_filter_expression(pkt_dns, "src == 10.0.0.5") is True
    assert win._eval_filter_expression(pkt_dns, "ip.src == 10.0.0.5") is True
    assert win._eval_filter_expression(pkt_dns, "dst == 8.8.8.8") is True
    assert win._eval_filter_expression(pkt_dns, "port == 53") is True
    assert win._eval_filter_expression(pkt_dns, "port == 80") is False
    
    # Test mitre contains
    assert win._eval_filter_expression(pkt_dns, "mitre contains T1568") is True
    assert win._eval_filter_expression(pkt_dns, "mitre contains T1059") is False

    # Test general text search
    assert win._eval_filter_expression(pkt_dns, "malw4r3") is True
    
    win.close()
