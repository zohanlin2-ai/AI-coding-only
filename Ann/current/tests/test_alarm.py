import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import shutil

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alarms.alarm_manager import Alarm, AlarmManager
from alarms.intent_parser import IntentParser


class TestAlarmModel(unittest.TestCase):
    def test_alarm_creation_and_serialization(self):
        dt = datetime.now() + timedelta(hours=1)
        alarm = Alarm(datetime_val=dt, label="Test meeting")
        
        # Verify initial values
        self.assertEqual(alarm.label, "Test meeting")
        self.assertEqual(alarm.datetime, dt)
        self.assertFalse(alarm.triggered)
        self.assertTrue(len(alarm.id) >= 4) # Short ID prefix should exist
        
        # Test dict conversion
        d = alarm.to_dict()
        self.assertEqual(d["id"], alarm.id)
        self.assertEqual(d["datetime"], dt.isoformat())
        self.assertEqual(d["label"], "Test meeting")
        self.assertFalse(d["triggered"])
        
        # Test from dict
        loaded = Alarm.from_dict(d)
        self.assertEqual(loaded.id, alarm.id)
        self.assertEqual(loaded.datetime, dt)
        self.assertEqual(loaded.label, "Test meeting")
        self.assertFalse(loaded.triggered)


class TestAlarmManager(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for test json file
        self.test_dir = tempfile.mkdtemp()
        self.test_file = Path(self.test_dir) / "alarms.json"
        
    def tearDown(self):
        # Clean up temp files
        shutil.rmtree(self.test_dir)

    def test_manager_ensure_store_creation(self):
        manager = AlarmManager(filepath=self.test_file)
        self.assertTrue(self.test_file.exists())
        self.assertEqual(len(manager.get_alarms()), 0)

    def test_add_and_list_alarms(self):
        manager = AlarmManager(filepath=self.test_file)
        dt = datetime.now() + timedelta(minutes=30)
        
        success, msg, alarm = manager.add_alarm(dt, "Drink water")
        self.assertTrue(success)
        self.assertEqual(msg, "鬧鐘設定成功")
        self.assertIsNotNone(alarm)
        self.assertEqual(alarm.label, "Drink water")
        
        alarms = manager.get_alarms()
        self.assertEqual(len(alarms), 1)
        self.assertEqual(alarms[0].label, "Drink water")
        
        # Verify persistence
        new_manager = AlarmManager(filepath=self.test_file)
        self.assertEqual(len(new_manager.get_alarms()), 1)
        self.assertEqual(new_manager.get_alarms()[0].label, "Drink water")

    def test_alarm_limits(self):
        manager = AlarmManager(filepath=self.test_file)
        dt = datetime.now() + timedelta(hours=1)
        
        # Add 10 alarms
        for i in range(10):
            success, msg, alarm = manager.add_alarm(dt, f"Alarm {i}")
            self.assertTrue(success)
            
        # Try to add the 11th alarm
        success, msg_list, alarm = manager.add_alarm(dt, "Alarm 11")
        self.assertFalse(success)
        self.assertIn("Alarm 0", msg_list)
        self.assertIn("Alarm 9", msg_list)
        self.assertIsNone(alarm)
        self.assertEqual(len(manager.get_alarms()), 10)

    def test_delete_alarm(self):
        manager = AlarmManager(filepath=self.test_file)
        dt = datetime.now() + timedelta(hours=1)
        
        _, _, alarm1 = manager.add_alarm(dt, "Breakfast")
        _, _, alarm2 = manager.add_alarm(dt, "Lunch")
        
        self.assertEqual(len(manager.get_alarms()), 2)
        
        # Delete by ID
        success = manager.delete_alarm(alarm1.id)
        self.assertTrue(success)
        self.assertEqual(len(manager.get_alarms()), 1)
        self.assertEqual(manager.get_alarms()[0].label, "Lunch")
        
        # Delete by prefix or non-existent
        self.assertFalse(manager.delete_alarm("non-existent"))
        
        # Delete by label
        success = manager.delete_alarm_by_label("lun")
        self.assertTrue(success)
        self.assertEqual(len(manager.get_alarms()), 0)

    def test_check_and_trigger_due_alarms(self):
        manager = AlarmManager(filepath=self.test_file)
        
        # Past alarm (due)
        dt_past = datetime.now() - timedelta(minutes=5)
        # Future alarm
        dt_future = datetime.now() + timedelta(minutes=5)
        
        # In order to add past alarm without clean_add validation filtering it,
        # we bypass the time cleanup in add_alarm check by injecting manually or patching
        alarm_past = Alarm(datetime_val=dt_past, label="Past Alarm")
        alarm_future = Alarm(datetime_val=dt_future, label="Future Alarm")
        
        manager.alarms = [alarm_past, alarm_future]
        manager.save_alarms()
        
        # Check triggers
        due = manager.check_and_trigger()
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0].label, "Past Alarm")
        self.assertTrue(due[0].triggered)
        
        # Verify the triggered one was removed from active manager
        self.assertEqual(len(manager.get_alarms()), 1)
        self.assertEqual(manager.get_alarms()[0].label, "Future Alarm")

    def test_update_alarm(self):
        manager = AlarmManager(filepath=self.test_file)
        dt = datetime.now() + timedelta(hours=1)
        
        _, _, alarm1 = manager.add_alarm(dt, "Breakfast Meeting")
        
        # Update by ID
        new_dt = dt + timedelta(hours=1)
        success, msg = manager.update_alarm(alarm_id=alarm1.id, new_datetime=new_dt)
        self.assertTrue(success)
        self.assertIn("已成功將鬧鐘", msg)
        self.assertEqual(manager.get_alarms()[0].datetime, new_dt)
        
        # Update by label substring
        new_dt2 = dt + timedelta(hours=2)
        success, msg = manager.update_alarm(target_alarm="breakfast", new_datetime=new_dt2)
        self.assertTrue(success)
        self.assertEqual(manager.get_alarms()[0].datetime, new_dt2)
        
        # Update by time substring
        time_str = new_dt2.strftime("%H:%M")
        new_dt3 = dt + timedelta(hours=3)
        success, msg = manager.update_alarm(target_alarm=time_str, new_datetime=new_dt3)
        self.assertTrue(success)
        self.assertEqual(manager.get_alarms()[0].datetime, new_dt3)
        
        # Update non-existent
        success, msg = manager.update_alarm(target_alarm="non-existent", new_datetime=new_dt3)
        self.assertFalse(success)
        self.assertIn("找不到符合條件", msg)


class TestIntentParser(unittest.TestCase):
    def test_keyword_pre_filtering(self):
        parser = IntentParser(base_url="http://mock", model="mock")
        
        # Alarm queries
        self.assertTrue(parser.should_parse("提醒我下午3點開會"))
        self.assertTrue(parser.should_parse("鬧鐘列表"))
        self.assertTrue(parser.should_parse("delete alarm 1"))
        
        # Normal chat
        self.assertFalse(parser.should_parse("你好嗎？請問什麼是微積分？"))
        self.assertFalse(parser.should_parse("寫一個 python 貪食蛇遊戲"))

    @patch("assistant.call_ollama")
    def test_intent_parsing_success(self, mock_call):
        parser = IntentParser(base_url="http://mock", model="mock")
        
        # Mock JSON response from Ollama
        json_resp = {
            "intent": "set_alarm",
            "time": "2026-05-28T08:00:00",
            "label": "吃藥",
            "alarm_id": None
        }
        mock_call.return_value = json.dumps(json_resp)
        
        res = parser.parse_intent("明天早上八點叫我，備註吃藥")
        self.assertEqual(res["intent"], "set_alarm")
        self.assertEqual(res["time"], "2026-05-28T08:00:00")
        self.assertEqual(res["label"], "吃藥")
        self.assertIsNone(res["alarm_id"])

    @patch("assistant.call_ollama")
    def test_intent_parsing_invalid_json_fallback(self, mock_call):
        parser = IntentParser(base_url="http://mock", model="mock")
        
        # Mock non-JSON response
        mock_call.return_value = "Sorry, I can't do that."
        
        res = parser.parse_intent("刪除鬧鐘 123")
        # Should fallback to regex rules
        self.assertEqual(res["intent"], "delete_alarm")
        self.assertEqual(res["alarm_id"], "123")

    def test_intent_parsing_update_fallback(self):
        parser = IntentParser(base_url="http://mock", model="mock")
        with patch("assistant.call_ollama", side_effect=Exception("offline")):
            res = parser.parse_intent("修改鬧鐘下午3點為下午4點")
            self.assertEqual(res["intent"], "update_alarm")
            self.assertEqual(res["target_alarm"], "下午3點")
