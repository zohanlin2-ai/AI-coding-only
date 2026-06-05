import sys
import os
import time
import json
from queue import Queue
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from security_daemon import ProcessCollector, FileCollector, NetworkCollector, SecurityEngine, DEFAULT_RULES, NormalizedEvent

def test_normalized_event():
    evt = NormalizedEvent(
        event_source="process_creation",
        data={"process_name": "cmd.exe", "command_line": "ping 127.0.0.1"}
    )
    assert evt.event_source == "process_creation"
    assert evt.data["process_name"] == "cmd.exe"
    assert evt.host is not None
    assert evt.timestamp is not None


def test_file_collector(tmp_path):
    q = Queue()
    collector = FileCollector(q, tmp_path, interval=0.1)
    
    # Run directory scan initially
    collector._scan_directory()
    assert q.empty()

    # Create file
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    collector._scan_directory()
    
    assert not q.empty()
    evt = q.get()
    assert evt.event_source == "file_activity"
    assert evt.data["operation"] == "created"
    assert evt.data["file_name"] == "test.txt"

    # Modify file
    time.sleep(0.01) # ensure mtime updates
    test_file.write_text("world")
    collector._scan_directory()
    
    assert not q.empty()
    evt = q.get()
    assert evt.event_source == "file_activity"
    assert evt.data["operation"] == "modified"


def test_security_engine_rules(tmp_path, monkeypatch):
    q = Queue()
    config = {"llm": {"base_url": "http://localhost:11434", "model": "gemma:2b"}}
    
    # Patch ALERTS_JSONL path to tmp_path / "alerts.jsonl"
    alerts_file = tmp_path / "alerts.jsonl"
    monkeypatch.setattr("security_daemon.ALERTS_JSONL", alerts_file)
    monkeypatch.setattr("security_daemon.LOGS_DIR", tmp_path)

    engine = SecurityEngine(q, DEFAULT_RULES, config)

    # Test R-001 Suspicious PowerShell creation
    evt_r001 = NormalizedEvent(
        event_source="process_creation",
        data={
            "process_name": "powershell.exe",
            "process_id": 1234,
            "command_line": "powershell.exe -enc IEX(New-Object Net.WebClient)...",
            "user": "testuser"
        }
    )
    engine._evaluate_event(evt_r001)

    assert alerts_file.exists()
    alerts = [json.loads(line) for line in alerts_file.read_text(encoding="utf-8").splitlines()]
    assert len(alerts) == 1
    assert alerts[0]["rule_id"] == "R-001"
    assert alerts[0]["severity"] == "high"
    assert "powershell" in alerts[0]["evidence"].lower()


def test_daemon_pause_resume(tmp_path):
    q = Queue()
    collector = FileCollector(q, tmp_path, interval=0.1)
    
    # Pause
    collector.pause()
    assert collector._paused.is_set()

    # Create file while paused
    test_file = tmp_path / "test_pause.txt"
    test_file.write_text("paused file")
    
    # Run loop logic manually as thread would check _paused
    # In run(), if paused is set, the polling logic is skipped.
    # We simulate this behavior:
    if not collector._paused.is_set():
        collector._scan_directory()
    
    assert q.empty()

    # Resume
    collector.resume()
    assert not collector._paused.is_set()
    collector._scan_directory()
    assert not q.empty()


def test_process_collector_unix_parsing(monkeypatch):
    class MockCompletedProcess:
        returncode = 0
        stdout = "  PID COMM COMMAND\n  100 bash /usr/bin/bash\n  101 python3 python3 security_daemon.py"

    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: MockCompletedProcess())

    q = Queue()
    collector = ProcessCollector(q)
    procs = collector._get_current_processes()
    
    assert len(procs) == 2
    assert procs[100]["Name"] == "bash"
    assert procs[100]["CommandLine"] == "/usr/bin/bash"
    assert procs[101]["Name"] == "python3"
    assert procs[101]["CommandLine"] == "python3 security_daemon.py"


def test_network_collector_parsing(monkeypatch):
    q = Queue()
    
    # 1. Test Windows Command Output Parsing (Powershell JSON)
    monkeypatch.setattr("platform.system", lambda: "Windows")
    
    class MockWindowsCompletedProcess:
        returncode = 0
        stdout = json.dumps([
            {
                "LocalAddress": "192.168.1.100",
                "LocalPort": 50505,
                "RemoteAddress": "8.8.8.8",
                "RemotePort": 53
            },
            {
                "LocalAddress": "10.0.0.10",
                "LocalPort": 1234,
                "RemoteAddress": "123.123.123.123",
                "RemotePort": 4444
            }
        ])
        
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: MockWindowsCompletedProcess())
    
    collector = NetworkCollector(q)
    conns = collector._get_active_connections()
    assert len(conns) == 2
    assert ("192.168.1.100", 50505, "8.8.8.8", 53) in conns
    assert ("10.0.0.10", 1234, "123.123.123.123", 4444) in conns

    # 2. Test Unix (Linux/macOS) netstat output parsing
    monkeypatch.setattr("platform.system", lambda: "Linux")
    
    class MockUnixCompletedProcess:
        returncode = 0
        # Linux netstat style with colons, and macOS style with dots
        stdout = (
            "Proto Recv-Q Send-Q Local Address           Foreign Address         State\n"
            "tcp        0      0 127.0.0.1:5000          8.8.8.8:443             ESTABLISHED\n"
            "tcp4       0      0 192.168.1.5.6000        1.1.1.1.80              ESTABLISHED\n"
            "tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN"
        )
        
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: MockUnixCompletedProcess())
    
    conns_unix = collector._get_active_connections()
    assert len(conns_unix) == 2
    assert ("127.0.0.1", 5000, "8.8.8.8", 443) in conns_unix
    assert ("192.168.1.5", 6000, "1.1.1.1", 80) in conns_unix


def test_r003_rule_matching(tmp_path, monkeypatch):
    q = Queue()
    config = {"llm": {"base_url": "http://localhost:11434", "model": "gemma:2b"}}
    
    # Patch alerts file paths
    alerts_file = tmp_path / "alerts.jsonl"
    monkeypatch.setattr("security_daemon.ALERTS_JSONL", alerts_file)
    monkeypatch.setattr("security_daemon.LOGS_DIR", tmp_path)

    engine = SecurityEngine(q, DEFAULT_RULES, config)

    # 1. Match suspicious IP (e.g. 8.8.8.8)
    evt_suspicious_ip = NormalizedEvent(
        event_source="network_activity",
        data={
            "local_ip": "192.168.1.100",
            "local_port": 50500,
            "remote_ip": "8.8.8.8",
            "remote_port": 443,
            "status": "ESTABLISHED",
            "user": "testuser"
        }
    )
    engine._evaluate_event(evt_suspicious_ip)
    
    assert alerts_file.exists()
    alerts = [json.loads(line) for line in alerts_file.read_text(encoding="utf-8").splitlines()]
    assert len(alerts) == 1
    assert alerts[0]["rule_id"] == "R-003"
    assert alerts[0]["severity"] == "medium"
    assert "8.8.8.8" in alerts[0]["evidence"]

    # 2. Match suspicious port (e.g. 4444)
    evt_suspicious_port = NormalizedEvent(
        event_source="network_activity",
        data={
            "local_ip": "192.168.1.100",
            "local_port": 50501,
            "remote_ip": "192.168.1.200",
            "remote_port": 4444,
            "status": "ESTABLISHED",
            "user": "testuser"
        }
    )
    engine._evaluate_event(evt_suspicious_port)
    
    alerts = [json.loads(line) for line in alerts_file.read_text(encoding="utf-8").splitlines()]
    assert len(alerts) == 2
    assert alerts[1]["rule_id"] == "R-003"
    assert "4444" in alerts[1]["evidence"]
