import json
import logging
from datetime import datetime
from pathlib import Path
import uuid
import threading

logger = logging.getLogger(__name__)

class Alarm:
    def __init__(self, datetime_val, label=None, id_val=None, created_at=None, triggered=False, repeat_pattern=None):
        self.id = id_val or str(uuid.uuid4())[:8]  # Keep it short/readable but unique enough for ID matching
        # Handle datetime_val as string or datetime object
        if isinstance(datetime_val, str):
            self.datetime = datetime.fromisoformat(datetime_val)
        else:
            self.datetime = datetime_val

        self.label = label
        
        if created_at is None:
            self.created_at = datetime.now()
        elif isinstance(created_at, str):
            self.created_at = datetime.fromisoformat(created_at)
        else:
            self.created_at = created_at
            
        self.triggered = triggered
        self.repeat_pattern = repeat_pattern

    def to_dict(self):
        return {
            "id": self.id,
            "datetime": self.datetime.isoformat(),
            "label": self.label,
            "created_at": self.created_at.isoformat(),
            "triggered": self.triggered,
            "repeat_pattern": self.repeat_pattern
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            datetime_val=data["datetime"],
            label=data.get("label"),
            id_val=data["id"],
            created_at=data.get("created_at"),
            triggered=data.get("triggered", False),
            repeat_pattern=data.get("repeat_pattern")
        )


class AlarmManager:
    MAX_ALARMS = 10

    def __init__(self, filepath=None):
        if filepath is None:
            self.filepath = Path.home() / ".ai-assistant" / "alarms.json"
        else:
            self.filepath = Path(filepath)
            
        self.lock = threading.Lock()
        self.alarms = []
        self._ensure_store_exists()
        self.load_alarms()

    def _ensure_store_exists(self):
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            if not self.filepath.exists():
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump([], f)
        except Exception as e:
            logger.error("Failed to create alarm store directory: %s", e)

    def _calculate_next_occurrence(self, current_dt: datetime, repeat_pattern: str, now: datetime) -> datetime:
        from datetime import timedelta
        if not repeat_pattern:
            return current_dt

        # 1. daily
        if repeat_pattern == "daily":
            next_dt = current_dt + timedelta(days=1)
            while next_dt <= now:
                next_dt += timedelta(days=1)
            return next_dt

        # 2. weekly:[days] (e.g. weekly:1,2,3,4,5 where 1=Mon, 7=Sun)
        if repeat_pattern.startswith("weekly:"):
            try:
                days_str = repeat_pattern.split(":")[1]
                target_days = [int(d) for d in days_str.split(",")]
            except Exception:
                target_days = [1, 2, 3, 4, 5, 6, 7] # Fallback to daily if invalid format
                
            next_dt = current_dt + timedelta(days=1)
            while next_dt.isoweekday() not in target_days or next_dt <= now:
                next_dt += timedelta(days=1)
            return next_dt

        # 3. interval:[minutes] (e.g. interval:1)
        if repeat_pattern.startswith("interval:"):
            try:
                minutes = int(repeat_pattern.split(":")[1])
            except Exception:
                minutes = 1
                
            next_dt = current_dt + timedelta(minutes=minutes)
            while next_dt <= now:
                next_dt += timedelta(minutes=minutes)
            return next_dt

        return current_dt

    def load_alarms(self):
        with self.lock:
            if not self.filepath.exists():
                self.alarms = []
                return
            
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                all_alarms = [Alarm.from_dict(d) for d in data]
                
                # Filter out expired (past time & triggered) alarms, advance repeating alarms
                now = datetime.now()
                self.alarms = []
                for alarm in all_alarms:
                    if alarm.repeat_pattern:
                        if alarm.datetime <= now:
                            alarm.datetime = self._calculate_next_occurrence(alarm.datetime, alarm.repeat_pattern, now)
                            alarm.triggered = False
                        self.alarms.append(alarm)
                    else:
                        if not (alarm.triggered or alarm.datetime < now):
                            self.alarms.append(alarm)
                
                # If clean-up happened, save back immediately
                if len(self.alarms) != len(all_alarms):
                    self._save_alarms_unlocked()
                    
            except Exception as e:
                logger.error("Error loading alarms, starting fresh. Details: %s", e)
                self.alarms = []

    def _save_alarms_unlocked(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump([alarm.to_dict() for alarm in self.alarms], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save alarms to %s: %s", self.filepath, e)

    def save_alarms(self):
        with self.lock:
            self._save_alarms_unlocked()

    def add_alarm(self, datetime_val, label=None, repeat_pattern=None) -> tuple[bool, str, Alarm | None]:
        """
        Adds a new alarm. Checks active alarm count first.
        Returns:
            (success, message, alarm_object)
        """
        with self.lock:
            # Clean up first to ensure accurate count
            now = datetime.now()
            active_alarms = []
            for alarm in self.alarms:
                if alarm.repeat_pattern:
                    if alarm.datetime <= now:
                        alarm.datetime = self._calculate_next_occurrence(alarm.datetime, alarm.repeat_pattern, now)
                        alarm.triggered = False
                    active_alarms.append(alarm)
                else:
                    if not (alarm.triggered or alarm.datetime < now):
                        active_alarms.append(alarm)
            self.alarms = active_alarms
            
            if len(self.alarms) >= self.MAX_ALARMS:
                # Return the list of current alarms to facilitate deletion selection
                alarms_list = "\n".join(
                    f"- [ID: {a.id}] {a.datetime.strftime('%Y-%m-%d %H:%M')} — {a.label or '無備註'}"
                    for a in self.alarms
                )
                return False, alarms_list, None
            
            alarm = Alarm(datetime_val=datetime_val, label=label, repeat_pattern=repeat_pattern)
            self.alarms.append(alarm)
            self._save_alarms_unlocked()
            return True, "鬧鐘設定成功", alarm

    def _alarm_matches_target(self, alarm, target: str) -> bool:
        if not target:
            return False
            
        target_lower = target.lower().strip()
        
        # 1. Match by ID (exact or prefix)
        if alarm.id == target_lower or alarm.id.startswith(target_lower):
            return True
            
        # 2. Match by label substring (bidirectional)
        if alarm.label and (target_lower in alarm.label.lower() or alarm.label.lower() in target_lower):
            return True
            
        # 3. Match by time substring (e.g. "15:00" or "下午3點")
        alarm_time_str = alarm.datetime.strftime("%H:%M")
        if target_lower in alarm_time_str or alarm_time_str in target_lower:
            return True
            
        # 4. Match by relative date names
        now_date = datetime.now().date()
        alarm_date = alarm.datetime.date()
        delta_days = (alarm_date - now_date).days
        
        relative_names = []
        if delta_days == 0:
            relative_names.extend(["今天", "today"])
        elif delta_days == 1:
            relative_names.extend(["明天", "明早", "明晚", "tomorrow", "一天後", "1天後", "1 day later"])
        elif delta_days == 2:
            relative_names.extend(["後天", "兩天後", "2天後", "2 days later"])
        elif delta_days == 3:
            relative_names.extend(["大後天", "三天後", "3天後", "3 days later"])
        elif delta_days > 3:
            relative_names.extend([f"{delta_days}天後", f"{delta_days} days later"])
        elif delta_days < 0:
            relative_names.extend(["昨天", "yesterday"])
            
        for name in relative_names:
            if name in target_lower or target_lower in name:
                return True
                
        # 5. Match by explicit date formats
        date_formats = [
            alarm.datetime.strftime("%Y-%m-%d"),
            alarm.datetime.strftime("%m-%d"),
            alarm.datetime.strftime("%m/%d"),
            f"{alarm.datetime.month}月{alarm.datetime.day}日",
            f"{alarm.datetime.month}月{alarm.datetime.day}號",
            f"{alarm.datetime.month}/{alarm.datetime.day}",
        ]
        for fmt in date_formats:
            if fmt in target_lower or target_lower in fmt:
                return True
                
        return False

    def delete_alarm(self, alarm_id: str) -> bool:
        """Deletes an alarm by its ID (exact match or prefix)."""
        with self.lock:
            matched_index = -1
            for idx, alarm in enumerate(self.alarms):
                if alarm.id == alarm_id or alarm.id.startswith(alarm_id):
                    matched_index = idx
                    break
            
            if matched_index != -1:
                self.alarms.pop(matched_index)
                self._save_alarms_unlocked()
                return True
            return False

    def delete_alarm_by_label(self, label: str) -> bool:
        """Deletes an alarm by label matching."""
        with self.lock:
            matched_index = -1
            for idx, alarm in enumerate(self.alarms):
                if alarm.label and (label.lower() in alarm.label.lower() or alarm.label.lower() in label.lower()):
                    matched_index = idx
                    break
            
            if matched_index != -1:
                self.alarms.pop(matched_index)
                self._save_alarms_unlocked()
                return True
            return False

    def delete_alarm_by_target(self, target: str) -> bool:
        """
        Deletes an alarm matching the target string (which could be ID, label substring, or time substring).
        """
        if not target:
            return False
            
        with self.lock:
            matched_idx = -1
            for idx, alarm in enumerate(self.alarms):
                if self._alarm_matches_target(alarm, target):
                    matched_idx = idx
                    break
                        
            if matched_idx != -1:
                self.alarms.pop(matched_idx)
                self._save_alarms_unlocked()
                return True
                
            return False

    def get_alarms(self) -> list[Alarm]:
        with self.lock:
            # Clean expired/update repeating first
            now = datetime.now()
            active_alarms = []
            for alarm in self.alarms:
                if alarm.repeat_pattern:
                    if alarm.datetime <= now:
                        alarm.datetime = self._calculate_next_occurrence(alarm.datetime, alarm.repeat_pattern, now)
                        alarm.triggered = False
                    active_alarms.append(alarm)
                else:
                    if not (alarm.triggered or alarm.datetime < now):
                        active_alarms.append(alarm)
            self.alarms = active_alarms
            return list(self.alarms)

    def check_and_trigger(self) -> list[Alarm]:
        """
        Check for any active alarms that are due.
        Marks them as triggered and updates the persistent store.
        """
        now = datetime.now()
        due_alarms = []
        
        with self.lock:
            updated_alarms = []
            for alarm in self.alarms:
                if not alarm.triggered and now >= alarm.datetime:
                    due_alarms.append(alarm)
                    if alarm.repeat_pattern:
                        next_dt = self._calculate_next_occurrence(alarm.datetime, alarm.repeat_pattern, now)
                        alarm.datetime = next_dt
                        alarm.triggered = False # Reset triggered for next round
                        updated_alarms.append(alarm)
                    else:
                        alarm.triggered = True
                else:
                    updated_alarms.append(alarm)
            
            if due_alarms:
                self.alarms = updated_alarms
                self._save_alarms_unlocked()
                
        return due_alarms

    def update_alarm(self, alarm_id: str = None, target_alarm: str = None, new_datetime = None) -> tuple[bool, str]:
        """
        Updates an alarm matching the criteria to a new datetime.
        Returns:
            (success, message)
        """
        if not new_datetime:
            return False, "未指定新的鬧鐘時間。"
            
        with self.lock:
            matched_alarm = None
            if alarm_id:
                for alarm in self.alarms:
                    if alarm.id == alarm_id or alarm.id.startswith(alarm_id):
                        matched_alarm = alarm
                        break
                        
            if not matched_alarm and target_alarm:
                for alarm in self.alarms:
                    if self._alarm_matches_target(alarm, target_alarm):
                        matched_alarm = alarm
                        break
                        
            if matched_alarm:
                old_time_str = matched_alarm.datetime.strftime("%Y-%m-%d %H:%M")
                matched_alarm.datetime = new_datetime
                matched_alarm.triggered = False # Reset triggered state
                self._save_alarms_unlocked()
                return True, f"已成功將鬧鐘（原時間: {old_time_str}，備註: {matched_alarm.label or '無'}）更改為 {new_datetime.strftime('%Y-%m-%d %H:%M')}。"
                
            return False, f"找不到符合條件 '{target_alarm or alarm_id}' 的鬧鐘。"
