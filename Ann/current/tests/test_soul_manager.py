import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from soul_manager import SoulManager
from slash_commands import handle_slash_command, SlashResult

class DummyController:
    def __init__(self):
        self.soul_manager = SoulManager()
        self.llm_model = "dummy-model"
        self.ollama_client = None


def test_default_state() -> None:
    sm = SoulManager()
    assert sm.mood == "Neutral"
    assert sm.energy == 100
    assert "Neutral" in sm.get_system_instruction()
    assert "accuracy" in sm.get_system_instruction()


def test_positive_keywords() -> None:
    sm = SoulManager()
    # Positive keyword should increase energy and set mood to Warm
    sm.energy = 80
    sm.update("這真是一個棒的功能，謝謝！")
    assert sm.mood == "Warm"
    assert sm.energy == 90

    # Cap at 100
    sm.update("Awesome work!")
    assert sm.energy == 100


def test_negative_keywords() -> None:
    sm = SoulManager()
    # Negative keyword should decrease energy and set mood to Professional (if energy >= 40)
    sm.energy = 80
    sm.update("你這個笨蛋，真爛！")
    assert sm.mood == "Professional"
    assert sm.energy == 60

    # Decrease further below 40 -> shifts to Subdued
    sm.update("這速度也太慢了，真差")
    assert sm.energy == 40
    
    sm.update("太差勁了")
    assert sm.energy == 20
    assert sm.mood == "Subdued"


def test_neutral_gradual_restore() -> None:
    sm = SoulManager()
    sm.energy = 80
    sm.mood = "Neutral"
    sm.update("哈囉，今天天氣如何？")
    assert sm.energy == 82
    assert sm.mood == "Neutral"


def test_reset() -> None:
    sm = SoulManager()
    sm.mood = "Warm"
    sm.energy = 50
    sm.reset()
    assert sm.mood == "Neutral"
    assert sm.energy == 100


def test_slash_command_soul() -> None:
    controller = DummyController()
    res = handle_slash_command("/soul", controller, Path(__file__).parent.parent.parent)
    assert res.handled is True
    assert "Neutral" in res.reply
    assert "100/100" in res.reply

    # Trigger change
    controller.soul_manager.mood = "Warm"
    controller.soul_manager.energy = 90
    res2 = handle_slash_command("/soul", controller, Path(__file__).parent.parent.parent)
    assert "Warm" in res2.reply
    assert "90/100" in res2.reply

    # Trigger reset via slash command
    res_reset = handle_slash_command("/soul reset", controller, Path(__file__).parent.parent.parent)
    assert res_reset.handled is True
    assert "defaults" in res_reset.reply
    assert controller.soul_manager.mood == "Neutral"
    assert controller.soul_manager.energy == 100
