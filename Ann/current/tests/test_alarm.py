# -*- coding: utf-8 -*-
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

    def test_delete_alarm_by_target(self):
        manager = AlarmManager(filepath=self.test_file)
        dt = datetime.now() + timedelta(hours=1)
        
        _, _, alarm1 = manager.add_alarm(dt, "Breakfast")
        _, _, alarm2 = manager.add_alarm(dt, "Meeting")
        
        self.assertEqual(len(manager.get_alarms()), 2)
        
        # Match by ID
        self.assertTrue(manager.delete_alarm_by_target(alarm1.id))
        self.assertEqual(len(manager.get_alarms()), 1)
        
        # Match by label substring
        self.assertTrue(manager.delete_alarm_by_target("meet"))
        self.assertEqual(len(manager.get_alarms()), 0)
        
        # Add another and match by time substring
        _, _, alarm3 = manager.add_alarm(dt, "Dinner")
        time_str = dt.strftime("%H:%M")
        self.assertTrue(manager.delete_alarm_by_target(time_str))
        self.assertEqual(len(manager.get_alarms()), 0)
        
        # Non-existent
        self.assertFalse(manager.delete_alarm_by_target("non-existent"))

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
        
        # Update by relative date (e.g., "tomorrow", "明天", "後天", "兩天後")
        dt_2days = datetime.now() + timedelta(days=2)
        _, _, alarm2 = manager.add_alarm(dt_2days, "Vacation")
        new_dt4 = dt_2days + timedelta(hours=1)
        success, msg = manager.update_alarm(target_alarm="兩天後", new_datetime=new_dt4)
        self.assertTrue(success)
        updated_alarm2 = [a for a in manager.get_alarms() if a.label == "Vacation"][0]
        self.assertEqual(updated_alarm2.datetime, new_dt4)

        # Update by explicit date format (e.g., "5/29")
        new_dt5 = dt_2days + timedelta(hours=2)
        date_str = dt_2days.strftime("%m/%d")
        success, msg = manager.update_alarm(target_alarm=date_str, new_datetime=new_dt5)
        self.assertTrue(success)
        updated_alarm2 = [a for a in manager.get_alarms() if a.label == "Vacation"][0]
        self.assertEqual(updated_alarm2.datetime, new_dt5)

        # Update non-existent
        success, msg = manager.update_alarm(target_alarm="non-existent", new_datetime=new_dt3)
        self.assertFalse(success)
        self.assertIn("找不到符合條件", msg)

    def test_calculate_next_occurrence(self):
        manager = AlarmManager(filepath=self.test_file)
        # 1. daily
        base_dt = datetime(2026, 5, 27, 10, 0, 0)
        now_dt = datetime(2026, 5, 27, 12, 0, 0)
        next_dt = manager._calculate_next_occurrence(base_dt, "daily", now_dt)
        self.assertEqual(next_dt, datetime(2026, 5, 28, 10, 0, 0))

        # 2. weekly (2026-05-27 is Wed=3, next Wed is 2026-06-03)
        base_dt = datetime(2026, 5, 27, 10, 0, 0)
        now_dt = datetime(2026, 5, 28, 10, 0, 0)
        next_dt = manager._calculate_next_occurrence(base_dt, "weekly:3", now_dt)
        self.assertEqual(next_dt, datetime(2026, 6, 3, 10, 0, 0))

        # 3. interval
        base_dt = datetime(2026, 5, 27, 10, 0, 0)
        now_dt = datetime(2026, 5, 27, 10, 12, 0)
        next_dt = manager._calculate_next_occurrence(base_dt, "interval:5", now_dt)
        self.assertEqual(next_dt, datetime(2026, 5, 27, 10, 15, 0))

    def test_repeating_alarm_trigger_lifecycle(self):
        manager = AlarmManager(filepath=self.test_file)
        dt_past = datetime.now() - timedelta(seconds=30)
        success, msg, alarm = manager.add_alarm(dt_past, "Recur Test", "interval:1")
        self.assertTrue(success)
        self.assertEqual(alarm.repeat_pattern, "interval:1")
        
        due = manager.check_and_trigger()
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0].label, "Recur Test")
        
        active = manager.get_alarms()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].label, "Recur Test")
        self.assertTrue(active[0].datetime > datetime.now())
        self.assertFalse(active[0].triggered)

    def test_alarm_id_sequential_and_recycling(self):
        manager = AlarmManager(filepath=self.test_file)
        dt = datetime.now() + timedelta(hours=1)

        # Add three alarms
        _, _, a1 = manager.add_alarm(dt, "Alarm 1")
        _, _, a2 = manager.add_alarm(dt, "Alarm 2")
        _, _, a3 = manager.add_alarm(dt, "Alarm 3")

        self.assertEqual(a1.id, "a1")
        self.assertEqual(a2.id, "a2")
        self.assertEqual(a3.id, "a3")

        # Delete a2
        self.assertTrue(manager.delete_alarm("a2"))

        # Next alarm should recycle "a2"
        _, _, a_new = manager.add_alarm(dt, "Alarm New")
        self.assertEqual(a_new.id, "a2")

        # Following alarm should get "a4"
        _, _, a_next = manager.add_alarm(dt, "Alarm Next")
        self.assertEqual(a_next.id, "a4")

    def test_update_alarm_flow_success_and_ambiguity(self):
        manager = AlarmManager(filepath=self.test_file)
        dt = datetime.now() + timedelta(hours=1)

        # Add two alarms with same label
        _, _, a1 = manager.add_alarm(dt, "Meeting")
        _, _, a2 = manager.add_alarm(dt + timedelta(hours=1), "Meeting")

        # Attempt ambiguous update (by label substring)
        new_dt = dt + timedelta(hours=2)
        success, msg, matches = manager.update_alarm_flow(target_alarm="Meeting", new_datetime=new_dt)
        self.assertFalse(success)
        self.assertEqual(len(matches), 2)
        self.assertIn("找到了多個", msg)

        # Successful update of label and time by exact ID (case-insensitive)
        success, msg, matches = manager.update_alarm_flow(alarm_id="A1", new_datetime=new_dt, new_label="Morning Meeting")
        self.assertTrue(success)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].id, "a1")
        self.assertEqual(matches[0].label, "Morning Meeting")
        self.assertEqual(matches[0].datetime, new_dt)

        # Verify a2 is untouched
        self.assertEqual(a2.label, "Meeting")

    def test_delete_alarm_flow_success_and_ambiguity(self):
        manager = AlarmManager(filepath=self.test_file)
        dt = datetime.now() + timedelta(hours=1)

        # Add two alarms with same label
        _, _, a1 = manager.add_alarm(dt, "Gym")
        _, _, a2 = manager.add_alarm(dt + timedelta(hours=1), "Gym")

        # Attempt ambiguous delete
        success, msg, matches = manager.delete_alarm_flow(target_alarm="Gym")
        self.assertFalse(success)
        self.assertEqual(len(matches), 2)
        self.assertEqual(len(manager.get_alarms()), 2)

        # Successful delete by ID
        success, msg, matches = manager.delete_alarm_flow(alarm_id="a2")
        self.assertTrue(success)
        self.assertEqual(len(matches), 1)
        self.assertEqual(len(manager.get_alarms()), 1)
        self.assertEqual(manager.get_alarms()[0].id, "a1")


class TestIntentParser(unittest.TestCase):
    def test_keyword_pre_filtering(self):
        parser = IntentParser(base_url="http://mock", model="mock")
        
        # Alarm queries
        self.assertTrue(parser.should_parse("\u63d0\u9192\u6211\u4e0b\u53483\u9ede\u958b\u6703"))
        self.assertTrue(parser.should_parse("\u9b27\u9418\u5217\u8868"))
        self.assertTrue(parser.should_parse("delete alarm 1"))
        
        # Normal chat
        self.assertFalse(parser.should_parse("\u4f60\u597d\u55ce\uff1f\u8acb\u554f\u4ec0\u9ebc\u662f\u5fae\u7a4d\u5206\uff1f"))
        self.assertFalse(parser.should_parse("\u5beb\u4e00\u500b python \u8caa\u98df\u86c7\u904a\u6232"))

    @patch("ollama_client.OllamaClient.chat")
    def test_intent_parsing_success(self, mock_chat):
        parser = IntentParser(base_url="http://mock", model="mock")
        
        # Mock JSON response from Ollama
        json_resp = {
            "intent": "set_alarm",
            "time": "2026-05-28T08:00:00",
            "label": "\u5403\u85e5",
            "alarm_id": None
        }
        mock_chat.return_value = json.dumps(json_resp)
        
        res = parser.parse_intent("\u660e\u5929\u65e9\u4e0a\u516b\u9ede\u53eb\u6211\uff0c\u5099\u8a3b\u5403\u85e5")
        self.assertEqual(res["intent"], "set_alarm")
        self.assertEqual(res["time"], "2026-05-28T08:00:00")
        self.assertEqual(res["label"], "\u5403\u85e5")
        self.assertIsNone(res["alarm_id"])

    @patch("ollama_client.OllamaClient.chat")
    def test_intent_parsing_invalid_json_fallback(self, mock_chat):
        parser = IntentParser(base_url="http://mock", model="mock")
        
        # Mock non-JSON response
        mock_chat.return_value = "Sorry, I can't do that."
        
        res = parser.parse_intent("刪除鬧鐘 123")
        # Should fallback to regex rules
        self.assertEqual(res["intent"], "delete_alarm")
        self.assertEqual(res["alarm_id"], "123")

    @patch("ollama_client.OllamaClient.chat", side_effect=Exception("offline"))
    def test_intent_parsing_update_fallback(self, mock_chat):
        parser = IntentParser(base_url="http://mock", model="mock")
        res = parser.parse_intent("修改鬧鐘下午3點為下午4點")
        self.assertEqual(res["intent"], "update_alarm")
        self.assertEqual(res["target_alarm"], "下午3點")

    def test_bidirectional_label_matching(self):
        # Create alarms and test matches target
        alarm = Alarm(datetime_val=datetime.now(), label="開會")
        # Use a temporary file path
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        try:
            manager = AlarmManager(filepath=temp_file.name)
            
            # Exact match
            self.assertTrue(manager._alarm_matches_target(alarm, "開會"))
            # Bidirectional substring matches
            self.assertTrue(manager._alarm_matches_target(alarm, "開會的鬧鐘"))
            self.assertTrue(manager._alarm_matches_target(alarm, "開"))
            
            # Test delete by target
            manager.alarms = [alarm]
            self.assertTrue(manager.delete_alarm_by_target("開會的鬧鐘"))
            self.assertEqual(len(manager.alarms), 0)
        finally:
            import os
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    @patch("ollama_client.OllamaClient.chat", side_effect=Exception("offline"))
    def test_regex_fallback_chinese_characters(self, mock_chat):
        parser = IntentParser(base_url="http://mock", model="mock")
        res = parser.parse_intent("刪除開會")
        self.assertEqual(res["intent"], "delete_alarm")
        self.assertEqual(res["target_alarm"], "開會")
        self.assertIsNone(res["alarm_id"])

    @patch("ollama_client.OllamaClient.chat")
    def test_clean_val_null_dummy_values(self, mock_chat):
        parser = IntentParser(base_url="http://mock", model="mock")
        
        # Mock JSON response with string "無", "None", "null"
        json_resp = {
            "intent": "delete_alarm",
            "alarm_id": "\u7121",
            "target_alarm": "null",
            "label": "None"
        }
        mock_chat.return_value = json.dumps(json_resp)
        
        res = parser.parse_intent("\u522a\u9664\u9b27\u9418")
        self.assertEqual(res["intent"], "delete_alarm")
        self.assertIsNone(res["alarm_id"])
        self.assertIsNone(res["target_alarm"])
        self.assertIsNone(res["label"])
