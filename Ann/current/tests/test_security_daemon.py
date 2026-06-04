import sys
import os
import time
import json
from queue import Queue
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from security_daemon import ProcessCollector, FileCollector, SecurityEngine, DEFAULT_RULES, NormalizedEvent

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
