"""
security_daemon.py — Real-time security detection daemon for Ann.

Monitors process creations (via PowerShell) and file activities (via polling).
Evaluates rules (R-001 and R-002) and writes alerts to logs/alerts.jsonl.
Performs asynchronous LLM enrichment using Ollama.
"""
from __future__ import annotations

import os
import json
import socket
import logging
import platform
import threading
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue, Empty
from typing import Any

from ollama_client import OllamaClient

logger = logging.getLogger(__name__)

# Constants
CURRENT_DIR = Path(__file__).parent
BASE_DIR = CURRENT_DIR.parent
LOGS_DIR = BASE_DIR / "logs"
ALERTS_JSONL = LOGS_DIR / "alerts.jsonl"

# Default rules config (can be extended)
DEFAULT_RULES = [
    {
        "id": "R-001",
        "name": "Suspicious command interpreter usage",
        "severity": "high",
        "event_source": "process_creation",
        "mitre": {
            "tactic": "Execution",
            "technique_id": "T1059",
            "technique_name": "Command and Scripting Interpreter"
        },
        "csf": {"function": "Detect", "category": "DE.CM"},
        "logic": {
            "process_names": ["cmd.exe", "powershell.exe", "pwsh.exe", "bash", "sh"],
            "command_line_keywords": ["-enc", "iex", "curl", "wget", "invoke-webrequest"]
        },
        "response": {
            "recommended_actions": [
                "Review command line and parent process.",
                "Check user account context.",
                "Isolate host if execution appears malicious."
            ]
        }
    },
    {
        "id": "R-002",
        "name": "Possible ransomware file encryption activity",
        "severity": "critical",
        "event_source": "file_activity",
        "mitre": {
            "tactic": "Impact",
            "technique_id": "T1486",
            "technique_name": "Data Encrypted for Impact"
        },
        "csf": {"function": "Detect", "category": "DE.CM"},
        "logic": {
            "file_operation_threshold": 5,          # Lowered from 500 for easy manual testing/demo
            "extension_change_threshold": 2,       # Lowered from 100 for easy manual testing/demo
            "suspicious_extensions": [".locked", ".encrypted", ".crypt"]
        },
        "response": {
            "recommended_actions": [
                "Isolate affected endpoint immediately.",
                "Disable suspected user account.",
                "Preserve process, file, and network evidence.",
                "Validate backup availability."
            ]
        }
    }
]


class NormalizedEvent:
    def __init__(self, event_source: str, data: dict[str, Any]):
        self.event_source = event_source
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.host = socket.gethostname()
        self.data = data


class ProcessCollector(threading.Thread):
    """Monitors running processes (cross-platform)."""
    def __init__(self, event_queue: Queue, interval: float = 3.0):
        super().__init__(daemon=True, name="ProcessCollector")
        self.event_queue = event_queue
        self.interval = interval
        self._stop_event = threading.Event()
        self._paused = threading.Event()
        self.seen_pids: set[int] = set()
        self.is_healthy_flag = True

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def run(self) -> None:
        # Initialize seen_pids so we don't alert on startup processes
        self._get_current_processes()
        logger.info("ProcessCollector initialized with %d processes", len(self.seen_pids))

        while not self._stop_event.is_set():
            if self._paused.is_set():
                self._stop_event.wait(self.interval)
                continue
            try:
                current_procs = self._get_current_processes()
                for pid, proc in current_procs.items():
                    if pid not in self.seen_pids:
                        # New process detected!
                        evt = NormalizedEvent(
                            event_source="process_creation",
                            data={
                                "process_name": proc.get("Name", "").lower(),
                                "process_id": pid,
                                "command_line": proc.get("CommandLine") or "",
                                "user": os.getlogin() if hasattr(os, "getlogin") else "system"
                            }
                        )
                        self.event_queue.put(evt)
                self.seen_pids = set(current_procs.keys())
                self.is_healthy_flag = True
            except Exception as e:
                logger.error("Error in ProcessCollector loop: %s", e)
                self.is_healthy_flag = False
            self._stop_event.wait(self.interval)

    def stop(self) -> None:
        self._stop_event.set()

    def is_healthy(self) -> bool:
        return self.is_healthy_flag

    def _get_current_processes(self) -> dict[int, dict[str, Any]]:
        """Executes a platform-specific command to grab current processes."""
        procs = {}
        system = platform.system()
        if system == "Windows":
            try:
                # Get processes via PowerShell
                cmd = ["powershell", "-NoProfile", "-Command", 
                       "Get-CimInstance Win32_Process | Select-Object Name, ProcessId, CommandLine | ConvertTo-Json"]
                res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=10)
                if res.returncode == 0 and res.stdout.strip():
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        pid = item.get("ProcessId")
                        if pid is not None:
                            procs[pid] = item
            except Exception as e:
                logger.debug("Failed to list Windows processes: %s", e)
        else:
            # macOS or Linux: use ps command
            try:
                # pid, comm (command/process name), args (arguments)
                cmd = ["ps", "-eo", "pid,comm,args"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    lines = res.stdout.strip().split("\n")
                    if len(lines) > 1:
                        for line in lines[1:]:
                            parts = line.strip().split(None, 2)
                            if len(parts) >= 2:
                                try:
                                    pid = int(parts[0])
                                    name = parts[1]
                                    cmdline = parts[2] if len(parts) > 2 else name
                                    procs[pid] = {
                                        "Name": name,
                                        "ProcessId": pid,
                                        "CommandLine": cmdline
                                    }
                                except ValueError:
                                    continue
            except Exception as e:
                logger.debug("Failed to list Unix processes: %s", e)
        return procs


class FileCollector(threading.Thread):
    """Monitors directory for file creation, modification, and extension changes."""
    def __init__(self, event_queue: Queue, watch_path: Path, interval: float = 3.0):
        super().__init__(daemon=True, name="FileCollector")
        self.event_queue = event_queue
        self.watch_path = Path(watch_path)
        self.interval = interval
        self._stop_event = threading.Event()
        self._paused = threading.Event()
        self.file_states: dict[str, tuple[float, int]] = {}  # path -> (mtime, size)
        self.is_healthy_flag = True

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def run(self) -> None:
        LOGS_DIR.mkdir(exist_ok=True)
        # Scan initially
        self._scan_directory()
        logger.info("FileCollector watching %s with %d files initially", self.watch_path, len(self.file_states))

        while not self._stop_event.is_set():
            if self._paused.is_set():
                self._stop_event.wait(self.interval)
                continue
            try:
                self._scan_directory()
                self.is_healthy_flag = True
            except Exception as e:
                logger.error("Error in FileCollector loop: %s", e)
                self.is_healthy_flag = False
            self._stop_event.wait(self.interval)

    def stop(self) -> None:
        self._stop_event.set()

    def is_healthy(self) -> bool:
        return self.is_healthy_flag

    def _scan_directory(self) -> None:
        if not self.watch_path.exists():
            return

        current_states: dict[str, tuple[float, int]] = {}
        for root, dirs, files in os.walk(self.watch_path):
            # Prune noisy folders
            dirs[:] = [d for d in dirs if d not in (".git", "venv", ".pytest_cache", "__pycache__", "logs")]
            for f in files:
                filepath = Path(root) / f
                try:
                    stat = filepath.stat()
                    state = (stat.st_mtime, stat.st_size)
                    path_str = str(filepath.resolve())
                    current_states[path_str] = state

                    if path_str not in self.file_states:
                        # Created
                        self._trigger_event(path_str, "created")
                    elif self.file_states[path_str] != state:
                        # Modified
                        self._trigger_event(path_str, "modified")
                except Exception:
                    pass

        # Check for deleted files
        for path_str in list(self.file_states.keys()):
            if path_str not in current_states:
                self._trigger_event(path_str, "deleted")

        self.file_states = current_states

    def _trigger_event(self, path_str: str, op: str) -> None:
        p = Path(path_str)
        evt = NormalizedEvent(
            event_source="file_activity",
            data={
                "path": path_str,
                "file_name": p.name,
                "operation": op,
                "new_extension": p.suffix.lower(),
                "user": os.getlogin() if hasattr(os, "getlogin") else "system"
            }
        )
        self.event_queue.put(evt)


class SecurityEngine(threading.Thread):
    """Consumes normalized events and matches them against active rules."""
    def __init__(self, event_queue: Queue, rules: list[dict], config: dict):
        super().__init__(daemon=True, name="SecurityEngine")
        self.event_queue = event_queue
        self.rules = rules
        self.config = config
        self._stop_event = threading.Event()
        self.ollama_client = OllamaClient(config.get("llm", {}).get("base_url", "http://localhost:11434"))
        self.llm_model = config.get("llm", {}).get("model", "gemma:2b")
        
        # Sliding windows for R-002 file operations
        # Tracks timestamp list of operations per (host, user)
        self.file_ops_window: dict[str, list[float]] = {}
        self.extension_changes_window: dict[str, list[float]] = {}

    def run(self) -> None:
        logger.info("SecurityEngine running with %d rules", len(self.rules))
        while not self._stop_event.is_set():
            try:
                evt = self.event_queue.get(timeout=1.0)
                self._evaluate_event(evt)
                self.event_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error("Error evaluating event in engine: %s", e)

    def stop(self) -> None:
        self._stop_event.set()

    def _evaluate_event(self, evt: NormalizedEvent) -> None:
        # Clean expired window timestamps (> 300s old)
        now = time.time()
        self._clean_windows(now)

        for rule in self.rules:
            if rule.get("event_source") != evt.event_source:
                continue

            if rule["id"] == "R-001":
                # Suspicious command usage check
                proc_name = evt.data.get("process_name", "")
                cmd_line = evt.data.get("command_line", "").lower()
                matched_name = any(n in proc_name for n in rule["logic"]["process_names"])
                matched_kw = any(k in cmd_line for k in rule["logic"]["command_line_keywords"])
                if matched_name and matched_kw:
                    self._trigger_alert(rule, evt)

            elif rule["id"] == "R-002":
                # Ransomware sliding window check
                # Group by host/user
                user_key = f"{evt.host}|{evt.data.get('user', 'unknown')}"
                op = evt.data.get("operation")
                ext = evt.data.get("new_extension", "")

                if op in ("created", "modified", "deleted"):
                    self.file_ops_window.setdefault(user_key, []).append(now)

                if ext in rule["logic"]["suspicious_extensions"]:
                    self.extension_changes_window.setdefault(user_key, []).append(now)

                # Count matches
                ops_count = len(self.file_ops_window.get(user_key, []))
                ext_count = len(self.extension_changes_window.get(user_key, []))

                if ops_count >= rule["logic"]["file_operation_threshold"] and ext_count >= rule["logic"]["extension_change_threshold"]:
                    # Rule matched! Trigger alert
                    evt.data["file_operation_count_5m"] = ops_count
                    evt.data["extension_change_count_5m"] = ext_count
                    self._trigger_alert(rule, evt)

    def _clean_windows(self, now: float) -> None:
        # 5 minutes = 300 seconds window
        cutoff = now - 300.0
        for key in list(self.file_ops_window.keys()):
            self.file_ops_window[key] = [t for t in self.file_ops_window[key] if t > cutoff]
            if not self.file_ops_window[key]:
                del self.file_ops_window[key]
        for key in list(self.extension_changes_window.keys()):
            self.extension_changes_window[key] = [t for t in self.extension_changes_window[key] if t > cutoff]
            if not self.extension_changes_window[key]:
                del self.extension_changes_window[key]

    def _trigger_alert(self, rule: dict, evt: NormalizedEvent) -> None:
        # Create alert ID
        alert_id = f"A-{int(time.time())}"
        alert_record = {
            "id": alert_id,
            "rule_id": rule["id"],
            "title": rule["name"],
            "severity": rule["severity"],
            "mitre": rule["mitre"]["technique_id"],
            "host": evt.host,
            "user": evt.data.get("user", "system"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "status": "open",
            "evidence": evt.data.get("command_line") or evt.data.get("path") or "No command line raw info",
            "response": rule["response"]["recommended_actions"]
        }
        logger.warning("ALERT TRIGGERED: %s", alert_record["title"])

        # Write immediately to alerts.jsonl
        self._write_alert_to_file(alert_record)

        # Kick off asynchronous LLM enrichment
        threading.Thread(
            target=self._enrich_alert_async,
            args=(alert_record,),
            daemon=True,
            name=f"Enricher-{alert_id}"
        ).start()

    def _write_alert_to_file(self, alert: dict) -> None:
        try:
            LOGS_DIR.mkdir(exist_ok=True)
            # Append log
            with open(ALERTS_JSONL, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("Failed to write alert record to file: %s", e)

    def _enrich_alert_async(self, alert: dict) -> None:
        """Calls local Ollama client to enrich the alert with threat analysis."""
        logger.info("Enriching alert %s using Ollama...", alert["id"])
        prompt = (
            f"Please analyze the following security alert command/evidence for maliciousness:\n"
            f"Title: {alert['title']}\n"
            f"Evidence: {alert['evidence']}\n\n"
            f"Provide a brief threat summary, assessment, and recommended immediate action.\n"
            f"Respond ONLY in a strict JSON format matching this schema:\n"
            f'{{"verdict": "malicious/suspicious/benign", "summary": "...", "recommended_action": "..."}}'
        )

        try:
            messages = [{"role": "user", "content": prompt}]
            response_content = self.ollama_client.chat(self.llm_model, messages)
            # Attempt to parse json
            parsed = {}
            # Strip markdown code blocks if any
            clean_res = response_content.strip()
            if "```" in clean_res:
                lines = clean_res.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                clean_res = "\n".join(lines).strip()

            try:
                parsed = json.loads(clean_res)
            except Exception:
                parsed = {
                    "verdict": "suspicious",
                    "summary": response_content[:150],
                    "recommended_action": "Manually verify command payload."
                }

            # Update the file by reading all alerts, replacing ours, and rewriting
            self._update_alert_in_file(alert["id"], parsed)
            logger.info("Enrichment completed for alert %s", alert["id"])
        except Exception as e:
            logger.error("Ollama alert enrichment failed: %s", e)

    def _update_alert_in_file(self, alert_id: str, analysis: dict) -> None:
        if not ALERTS_JSONL.exists():
            return

        try:
            # Read all
            lines = []
            with open(ALERTS_JSONL, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        lines.append(json.loads(line.strip()))

            # Update target
            for alert in lines:
                if alert.get("id") == alert_id:
                    alert["llm_analysis"] = analysis
                    # Append analysis summary to recommended actions list
                    summary_msg = f"LLM Verdict ({analysis.get('verdict', 'unknown')}): {analysis.get('summary', '')}"
                    alert["response"].append(summary_msg)

            # Rewrite
            with open(ALERTS_JSONL, "w", encoding="utf-8") as f:
                for alert in lines:
                    f.write(json.dumps(alert, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("Failed to update alert file with enrichment: %s", e)


class SecurityDaemon:
    """Orchestrates event queue, collectors, and detection engine lifecycle."""
    _instance: SecurityDaemon | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, config: dict):
        if hasattr(self, "_initialized"):
            return
        self.config = config
        self.event_queue: Queue = Queue(maxsize=10000)
        self.process_collector = ProcessCollector(self.event_queue)
        self.file_collector = FileCollector(self.event_queue, BASE_DIR)
        self.engine = SecurityEngine(self.event_queue, DEFAULT_RULES, config)
        self.running = False
        self._initialized = True

    def start(self) -> None:
        if self.running:
            return
        logger.info("Starting SecurityDaemon services...")
        self.running = True
        # Start collectors & engine
        self.process_collector = ProcessCollector(self.event_queue)
        self.file_collector = FileCollector(self.event_queue, BASE_DIR)
        self.engine = SecurityEngine(self.event_queue, DEFAULT_RULES, self.config)

        self.process_collector.start()
        self.file_collector.start()
        self.engine.start()

    def stop(self) -> None:
        if not self.running:
            return
        logger.info("Stopping SecurityDaemon services...")
        self.running = False
        self.process_collector.stop()
        self.file_collector.stop()
        self.engine.stop()

        # Join threads
        self.process_collector.join(timeout=2.0)
        self.file_collector.join(timeout=2.0)
        self.engine.join(timeout=2.0)

    def pause(self) -> None:
        logger.info("Pausing SecurityDaemon collectors...")
        self.process_collector.pause()
        self.file_collector.pause()

    def resume(self) -> None:
        logger.info("Resuming SecurityDaemon collectors...")
        self.process_collector.resume()
        self.file_collector.resume()
