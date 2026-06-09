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

# Capture the real conflict-detection method before the autouse fixture stubs
# it out, so the dedicated conflict tests can invoke the genuine logic
# synchronously without being affected by the stub.
_REAL_DETECT_CONFLICT = MemoryManager._detect_and_resolve_conflict


@pytest.fixture
def temp_base_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def memory_manager(temp_base_dir):
    return MemoryManager(temp_base_dir, "http://localhost:11434", "gemma4:e4b")


@pytest.fixture(autouse=True)
def offline_ollama(monkeypatch):
    """
    Default every test to an 'offline' Ollama so that incidental background
    network activity is deterministic: add_memory()'s background conflict
    detection / organization threads and retrieve_memories()'s embedding
    lookups all degrade to no-op / keyword mode instead of hitting a real
    Ollama instance that may or may not be running on the test machine.

    Tests that need a specific LLM response patch requests.post themselves
    (via @patch), which overrides this fixture for the duration of the test.
    """
    import requests

    def _refuse(*args, **kwargs):
        raise requests.exceptions.ConnectionError("offline (test environment)")

    monkeypatch.setattr(requests, "post", _refuse)

    # add_memory() spawns a background conflict-detection thread; stub it so its
    # timing can never race with a test's own request mocking. Conflict logic is
    # exercised directly via _REAL_DETECT_CONFLICT in the dedicated tests.
    monkeypatch.setattr(MemoryManager, "_detect_and_resolve_conflict", lambda self, *a, **k: None)


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


# ---------------------------------------------------------------------------
# Phase 2 — usage statistics
# ---------------------------------------------------------------------------

def test_get_stats(memory_manager):
    memory_manager.add_memory("project", ["python"], "First memory", "", 0.9)
    memory_manager.add_memory("preference", ["coffee"], "Second memory", "", 0.8)
    memory_manager.delete_memory("M.1")

    stats = memory_manager.get_stats()
    assert stats["total"] == 2
    assert stats["active"] == 1
    assert stats["deleted"] == 1
    assert stats["outdated"] == 0
    assert stats["files"] == 1
    assert stats["enabled"] is True
    assert stats["size_kb"] >= 0


# ---------------------------------------------------------------------------
# Phase 2 — embedding helpers & semantic retrieval
# ---------------------------------------------------------------------------

def test_cosine_similarity():
    # Identical direction → 1.0; orthogonal → 0.0; opposite → -1.0
    assert MemoryManager._cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert MemoryManager._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert MemoryManager._cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)
    # Zero vector → 0.0 (no division by zero)
    assert MemoryManager._cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_retrieve_memories_embedding_mode(memory_manager, monkeypatch):
    memory_manager.add_memory("project", ["python", "pytest"], "Testing python project code", "", 0.9)
    memory_manager.add_memory("preference", ["coffee", "black"], "User prefers black coffee", "", 0.8)

    # Deterministic embedding map: query is close to the python memory,
    # orthogonal to the coffee one.
    vectors = {
        "How do I test my code?": [1.0, 0.0],
        "Testing python project code": [0.95, 0.05],
        "User prefers black coffee": [0.0, 1.0],
    }

    def fake_embed(self, text):
        return vectors.get(text)

    monkeypatch.setattr(MemoryManager, "_get_embedding", fake_embed)

    results = memory_manager.retrieve_memories("How do I test my code?")
    summaries = [r["summary"] for r in results]
    assert "Testing python project code" in summaries
    assert "User prefers black coffee" not in summaries


# ---------------------------------------------------------------------------
# Phase 2 — outdated marking & conflict detection
# ---------------------------------------------------------------------------

def test_mark_as_outdated(memory_manager):
    memory_manager.add_memory("preference", ["tea"], "User drinks tea", "", 0.9)
    assert memory_manager._mark_as_outdated("M.1") is True

    assert len(memory_manager.list_memories()) == 0
    stats = memory_manager.get_stats()
    assert stats["active"] == 0
    assert stats["outdated"] == 1
    assert stats["deleted"] == 0


@patch("requests.post")
def test_conflict_detection_marks_outdated(mock_post, memory_manager):
    memory_manager.add_memory("preference", ["coffee", "drink"], "User likes coffee", "", 0.9)

    # LLM judges the existing memory contradicts the new one.
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "CONFLICT: M.1"}}
    mock_post.return_value = mock_resp

    # New contradicting fact, same category + overlapping keywords.
    _REAL_DETECT_CONFLICT(memory_manager, "preference", ["coffee", "drink"], "User dislikes coffee")

    active = memory_manager.list_memories()
    assert all(u["id"] != "M.1" for u in active)
    stats = memory_manager.get_stats()
    assert stats["outdated"] == 1


@patch("requests.post")
def test_conflict_detection_no_conflict(mock_post, memory_manager):
    memory_manager.add_memory("preference", ["coffee", "drink"], "User likes coffee", "", 0.9)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "NONE"}}
    mock_post.return_value = mock_resp

    _REAL_DETECT_CONFLICT(memory_manager, "preference", ["coffee", "drink"], "User likes espresso too")

    # Nothing demoted.
    assert len(memory_manager.list_memories()) == 1
    assert memory_manager.get_stats()["outdated"] == 0


# ---------------------------------------------------------------------------
# Phase 2 — auto organization
# ---------------------------------------------------------------------------

def test_maybe_trigger_organization_flag(memory_manager):
    # Below threshold: flag stays False.
    memory_manager.add_memory("project", ["a"], "one", "", 0.9)
    with open(memory_manager.index_path, "r", encoding="utf-8") as f:
        assert json.load(f)["needs_organization"] is False

    # Force active count to the threshold, then trigger.
    import filelock
    lock = filelock.FileLock(memory_manager.lock_path)
    with lock:
        data = memory_manager._get_index_locked()
        data["active_memories"] = memory_manager._ORGANIZE_EVERY
        memory_manager._save_index_locked(data)
    memory_manager._maybe_trigger_organization()

    with open(memory_manager.index_path, "r", encoding="utf-8") as f:
        assert json.load(f)["needs_organization"] is True


@patch("requests.post")
def test_run_organization_merges_cluster(mock_post, memory_manager):
    # Three highly-similar memories (same category, ≥2 shared keywords, conf ≥0.7).
    for i in range(3):
        memory_manager.add_memory("project", ["python", "test", "code"], f"Note {i} about python testing", "", 0.9)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "Consolidated python testing notes"}}
    mock_post.return_value = mock_resp

    memory_manager._run_organization()

    active = memory_manager.list_memories()
    assert len(active) == 1
    merged = active[0]
    assert merged["summary"] == "Consolidated python testing notes"
    assert merged["source"] == "organization"

    # Originals demoted to outdated (not deleted).
    stats = memory_manager.get_stats()
    assert stats["outdated"] == 3
    assert stats["deleted"] == 0
