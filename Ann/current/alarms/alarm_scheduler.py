import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import PyQt6/PySide6 for QTimer
GUI_AVAILABLE = False
try:
    from PyQt6.QtCore import QTimer
    GUI_AVAILABLE = True
except ImportError:
    try:
        from PySide6.QtCore import QTimer
        GUI_AVAILABLE = True
    except ImportError:
        GUI_AVAILABLE = False


class AlarmScheduler:
    def __init__(self, alarm_manager, alarm_trigger):
        self.alarm_manager = alarm_manager
        self.alarm_trigger = alarm_trigger
        
        # CLI polling state
        self.cli_thread = None
        self.cli_stop_event = threading.Event()
        self.active_triggered_alarms = []
        self.cli_alert_thread = None
        self.cli_alert_stop = threading.Event()

        # GUI timer
        self.gui_timer = None
        self.gui_callback = None
        self.gui_widget = None

    # --- GUI Scheduling ---
    def start_gui_scheduler(self, widget, callback):
        """Starts a QTimer-based scheduler for PyQt/PySide GUI."""
        if not GUI_AVAILABLE:
            logger.warning("GUI scheduler cannot start: PyQt6/PySide6 not available.")
            return

        self.gui_widget = widget
        self.gui_callback = callback
        
        # Polling every 15 seconds to check for due alarms
        self.gui_timer = QTimer(widget)
        self.gui_timer.timeout.connect(self._check_and_dispatch_gui)
        self.gui_timer.start(15000) # 15 seconds polling
        logger.info("GUI Alarm Scheduler started with 15s interval.")

    def _check_and_dispatch_gui(self):
        due = self.alarm_manager.check_and_trigger()
        if due and self.gui_callback:
            for alarm in due:
                self.gui_callback(alarm)

    def stop_gui_scheduler(self):
        if self.gui_timer:
            self.gui_timer.stop()
            self.gui_timer = None

    # --- CLI Scheduling ---
    def start_cli_scheduler(self, callback):
        """Starts a background thread to check for due alarms in CLI mode."""
        self.cli_stop_event.clear()
        self.cli_thread = threading.Thread(target=self._run_cli_loop, args=(callback,), daemon=True)
        self.cli_thread.start()
        logger.info("CLI Alarm Scheduler background thread started.")

    def _run_cli_loop(self, callback):
        while not self.cli_stop_event.is_set():
            try:
                due = self.alarm_manager.check_and_trigger()
                if due:
                    for alarm in due:
                        callback(alarm)
            except Exception as e:
                logger.error("Error in CLI scheduler loop: %s", e)
            
            # Poll every 1 second
            time.sleep(1.0)

    def stop_cli_scheduler(self):
        self.cli_stop_event.set()
        if self.cli_thread:
            self.cli_thread.join(timeout=1.0)
            self.cli_thread = None
        self.stop_cli_alerts()

    def start_cli_alerts(self, alarm_label, alarm_time_str):
        """Spawns a thread that prints the alarm alert every 2 seconds."""
        self.stop_cli_alerts() # stop any previous one first
        self.cli_alert_stop.clear()
        self.cli_alert_thread = threading.Thread(
            target=self._run_cli_alerts, 
            args=(alarm_label, alarm_time_str), 
            daemon=True
        )
        self.cli_alert_thread.start()

    def _run_cli_alerts(self, label, time_str):
        while not self.cli_alert_stop.is_set():
            print(f"\n🔔 [鬧鐘提醒] {label} 時間到了！({time_str}) — (請按 Enter 鍵關閉鬧鐘)\nYou: ", end="", flush=True)
            time.sleep(2.0)

    def stop_cli_alerts(self):
        self.cli_alert_stop.set()
        if self.cli_alert_thread:
            self.cli_alert_thread.join(timeout=0.5)
            self.cli_alert_thread = None
