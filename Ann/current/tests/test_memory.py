import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_manager import MemoryManager


@pytest.fixture
def temp_base_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def memory_manager(temp_base_dir):
    return MemoryManager(temp_base_dir, "http://localhost:11434", "gemma4:e4b")


def test_setup_dirs(memory_manager, temp_base_dir):
    assert (temp_base_dir / "memory").exists()
    assert (temp_base_dir / "memory" / "memories").exists()
    assert (temp_base_dir / "memory" / "backup").exists()
    assert (temp_base_dir / "memory" / "trash").exists()
    assert (temp_base_dir / "memory" / "index.json").exists()


def test_validate_memory_unit(memory_manager):
    valid_unit = {
        "id": "M.1",
        "created_at": "2026-06-03T14:20:00+08:00",
        "updated_at": "2026-06-03T14:20:00+08:00",
        "category": "project",
        "keywords": ["local llm", "memory"],
        "summary": "Building a local LLM application",
        "details": "Using gemma4 model on Windows.",
        "confidence": 0.9,
        "status": "active",
        "source": "conversation"
    }
    assert memory_manager.validate_memory_unit(valid_unit) is True

    # Missing field
    invalid_unit = valid_unit.copy()
    del invalid_unit["confidence"]
    assert memory_manager.validate_memory_unit(invalid_unit) is False

    # Bad category
    invalid_unit = valid_unit.copy()
    invalid_unit["category"] = "invalid_category_123"
    assert memory_manager.validate_memory_unit(invalid_unit) is False

    # Too many keywords
    invalid_unit = valid_unit.copy()
    invalid_unit["keywords"] = ["a", "b", "c", "d", "e", "f"]
    assert memory_manager.validate_memory_unit(invalid_unit) is False

    # Bad timestamp
    invalid_unit = valid_unit.copy()
    invalid_unit["created_at"] = "2026-15-40"
    assert memory_manager.validate_memory_unit(invalid_unit) is False


def test_add_memory(memory_manager):
    unit = memory_manager.add_memory(
        category="project",
        keywords=["gemma", "python"],
        summary="Developing memory manager",
        details="Phase 1 MVP implementation",
        confidence=0.95,
        source="manual"
    )
    assert unit is not None
    assert unit["id"] == "M.1"
    assert unit["category"] == "project"
    assert "gemma" in unit["keywords"]
    assert unit["summary"] == "Developing memory manager"

    # Verify written file
    today_file = memory_manager.get_today_file_path()
    assert today_file.exists()
    with open(today_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["memories"]) == 1
    assert data["memories"][0]["id"] == "M.1"

    # Verify index updated
    with open(memory_manager.index_path, "r", encoding="utf-8") as f:
        idx = json.load(f)
    assert idx["total_memories"] == 1
    assert idx["active_memories"] == 1


def test_retrieve_memories(memory_manager):
    # Add memories with keywords
    memory_manager.add_memory("project", ["python", "pytest"], "Testing python project code", "", 0.9)
    memory_manager.add_memory("preference", ["coffee", "black"], "User prefers black coffee", "", 0.8)
    memory_manager.add_memory("todo", ["pytest", "coverage"], "Write pytest coverage script", "", 0.7)

    # Search for pytest
    results = memory_manager.retrieve_memories("Can we run pytest?")
    assert len(results) == 2
    summaries = [r["summary"] for r in results]
    assert "Testing python project code" in summaries
    assert "Write pytest coverage script" in summaries
    assert "User prefers black coffee" not in summaries


def test_delete_memory(memory_manager):
    memory_manager.add_memory("project", ["python"], "Testing delete memory capability", "", 0.9)
    assert memory_manager.delete_memory("M.1") is True
    
    active = memory_manager.list_memories()
    assert len(active) == 0

    with open(memory_manager.index_path, "r", encoding="utf-8") as f:
        idx = json.load(f)
    assert idx["active_memories"] == 0
    assert idx["deleted_memories"] == 1


def test_edit_memory(memory_manager):
    memory_manager.add_memory("project", ["python"], "Testing edit", "Original details", 0.9)
    assert memory_manager.edit_memory("M.1", summary="Updated testing edit", details="New details") is True

    active = memory_manager.list_memories()
    assert len(active) == 1
    assert active[0]["summary"] == "Updated testing edit"
    assert active[0]["details"] == "New details"


def test_toggle(memory_manager):
    assert memory_manager.enabled is True
    memory_manager.toggle(False)
    assert memory_manager.enabled is False
    
    # Adding while disabled should return None and not write
    unit = memory_manager.add_memory("project", ["test"], "Should not save", "", 0.9, source="conversation")
    assert unit is None
    
    # Adding as manual source should still write even if disabled
    unit2 = memory_manager.add_memory("project", ["test"], "Manual save", "", 0.9, source="manual")
    assert unit2 is not None


@patch("requests.post")
def test_background_extraction_phase_1(mock_post, memory_manager):
    # Mock Ollama API response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {
            "content": json.dumps([{
                "category": "project",
                "keywords": ["ai", "assistant"],
                "summary": "User is building an AI assistant named Ann.",
                "details": "",
                "confidence": 0.95
            }])
        }
    }
    mock_post.return_value = mock_resp

    # Directly run target to verify functionality synchronously in test
    memory_manager._run_extraction_phase_1("I am building an AI assistant named Ann.")
    
    active = memory_manager.list_memories()
    assert len(active) == 1
    assert active[0]["summary"] == "User is building an AI assistant named Ann."
    assert "ai" in active[0]["keywords"]
