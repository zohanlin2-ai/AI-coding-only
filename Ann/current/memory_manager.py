import datetime
import json
import logging
import re
import threading
from pathlib import Path
from filelock import FileLock

logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = {"profile", "preference", "project", "todo", "event", "skill", "correction", "system"}
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


class MemoryManager:
    def __init__(self, base_dir: Path, base_url: str, model: str):
        self.base_dir = base_dir
        self.base_url = base_url
        self.model = model
        
        self.memory_dir = self.base_dir / "memory"
        self.memories_dir = self.memory_dir / "memories"
        self.backup_dir = self.memory_dir / "backup"
        self.trash_dir = self.memory_dir / "trash"
        self.index_path = self.memory_dir / "index.json"
        
        # Lock for cross-process and cross-thread access
        self.lock_path = self.memory_dir / "memory.lock"
        
        # Memory system toggle
        self.enabled = True
        
        self.setup_dirs()
        self._load_state_from_index()

    def setup_dirs(self) -> None:
        """Create required directories if they don't exist."""
        self.memory_dir.mkdir(exist_ok=True, parents=True)
        self.memories_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        self.trash_dir.mkdir(exist_ok=True)

    def _load_state_from_index(self) -> None:
        """Load state and index file, initialize if missing."""
        lock = FileLock(self.lock_path)
        with lock:
            if not self.index_path.exists():
                self._save_index_locked({
                    "schema_version": 1,
                    "last_organized": "",
                    "needs_organization": False,
                    "total_size_bytes": 0,
                    "total_memories": 0,
                    "active_memories": 0,
                    "outdated_memories": 0,
                    "deleted_memories": 0,
                    "enabled": True,
                    "files": []
                })
            else:
                try:
                    with open(self.index_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.enabled = data.get("enabled", True)
                except Exception as e:
                    logger.error("Failed to load memory index.json: %s", e)
                    self.enabled = True

    def _get_index_locked(self) -> dict:
        """Read the index file, caller must hold the lock."""
        try:
            if self.index_path.exists():
                with open(self.index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error("Error reading index: %s", e)
        return {
            "schema_version": 1,
            "last_organized": "",
            "needs_organization": False,
            "total_size_bytes": 0,
            "total_memories": 0,
            "active_memories": 0,
            "outdated_memories": 0,
            "deleted_memories": 0,
            "enabled": True,
            "files": []
        }

    def _save_index_locked(self, data: dict) -> None:
        """Write the index file, caller must hold the lock."""
        try:
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Error saving index: %s", e)

    def toggle(self, enable: bool) -> None:
        """Toggle memory system on or off."""
        self.enabled = enable
        lock = FileLock(self.lock_path)
        with lock:
            index_data = self._get_index_locked()
            index_data["enabled"] = enable
            self._save_index_locked(index_data)

    def validate_memory_unit(self, unit: dict) -> bool:
        """Validate if a memory unit conforms to the specification schemas."""
        required_fields = {"id", "created_at", "updated_at", "category", "keywords", "summary", "details", "confidence", "status", "source"}
        if not required_fields.issubset(unit.keys()):
            logger.warning("Memory validation failed: Missing required fields. Got fields: %s", list(unit.keys()))
            return False

        if unit["category"] not in ALLOWED_CATEGORIES:
            logger.warning("Memory validation failed: Invalid category '%s'", unit["category"])
            return False

        if not isinstance(unit["keywords"], list) or not (1 <= len(unit["keywords"]) <= 5):
            logger.warning("Memory validation failed: keywords must be a list of 1 to 5 items")
            return False

        for k in unit["keywords"]:
            if not isinstance(k, str):
                logger.warning("Memory validation failed: keyword '%s' is not a string", k)
                return False

        if not isinstance(unit["summary"], str) or not unit["summary"].strip():
            logger.warning("Memory validation failed: summary must be a non-empty string")
            return False

        if not isinstance(unit["details"], str):
            logger.warning("Memory validation failed: details must be a string")
            return False

        try:
            conf = float(unit["confidence"])
            if not (0.0 <= conf <= 1.0):
                logger.warning("Memory validation failed: confidence %s must be between 0.0 and 1.0", conf)
                return False
        except (ValueError, TypeError):
            logger.warning("Memory validation failed: confidence %s is not a float", unit["confidence"])
            return False

        if unit["status"] not in {"active", "outdated", "deleted"}:
            logger.warning("Memory validation failed: Invalid status '%s'", unit["status"])
            return False

        # Validate ISO 8601 timestamps
        for ts_field in ("created_at", "updated_at"):
            try:
                datetime.datetime.strptime(unit[ts_field], "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                # Try simple format if timezone fails
                try:
                    datetime.datetime.fromisoformat(unit[ts_field])
                except ValueError:
                    logger.warning("Memory validation failed: Invalid ISO timestamp %s: '%s'", ts_field, unit[ts_field])
                    return False
        return True

    def get_today_file_path(self) -> Path:
        """Returns the file path for today's memory JSON."""
        today_str = datetime.date.today().isoformat()
        return self.memories_dir / f"{today_str}_memory.json"

    def add_memory(self, category: str, keywords: list[str], summary: str, details: str, confidence: float, source: str = "conversation") -> dict | None:
        """Add a single memory unit. Thread-safe and cross-process safe."""
        if not self.enabled and source != "manual":
            return None

        if confidence < 0.40:
            logger.info("Discarding low confidence (%s) memory: %s", confidence, summary)
            return None

        # Clean keywords
        keywords = [str(k).strip().lower() for k in keywords[:5] if str(k).strip()]
        if not keywords:
            keywords = ["general"]

        tz = datetime.datetime.now().astimezone().tzinfo
        now_str = datetime.datetime.now(tz).replace(microsecond=0).isoformat()

        lock = FileLock(self.lock_path)
        with lock:
            index_data = self._get_index_locked()
            
            # Generate next ID
            total_memories = index_data.get("total_memories", 0) + 1
            memory_id = f"M.{total_memories}"

            unit = {
                "id": memory_id,
                "created_at": now_str,
                "updated_at": now_str,
                "category": category,
                "keywords": keywords,
                "summary": summary,
                "details": details,
                "confidence": confidence,
                "status": "active",
                "source": source
            }

            if not self.validate_memory_unit(unit):
                logger.error("Generated memory unit failed validation: %s", unit)
                return None

            # Load today's memory file
            today_path = self.get_today_file_path()
            today_data = {"memories": []}
            if today_path.exists():
                try:
                    with open(today_path, "r", encoding="utf-8") as f:
                        today_data = json.load(f)
                except Exception as e:
                    logger.error("Error reading today's memory file: %s", e)

            today_data["memories"].append(unit)

            # Write back today's file safely
            temp_path = today_path.with_suffix(".tmp")
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(today_data, f, ensure_ascii=False, indent=2)
                if temp_path.exists():
                    temp_path.replace(today_path)
            except Exception as e:
                logger.error("Error writing to today's memory file: %s", e)
                if temp_path.exists():
                    temp_path.unlink()
                return None

            # Update index
            index_data["total_memories"] = total_memories
            index_data["active_memories"] = index_data.get("active_memories", 0) + 1
            
            # Update file list in index
            filename = today_path.name
            file_entry = next((f for f in index_data["files"] if f["filename"] == filename), None)
            if file_entry:
                file_entry["size_bytes"] = today_path.stat().st_size
                file_entry["memory_count"] = len(today_data["memories"])
                file_entry["short_term"] = True
            else:
                index_data["files"].append({
                    "filename": filename,
                    "size_bytes": today_path.stat().st_size,
                    "memory_count": len(today_data["memories"]),
                    "short_term": True
                })

            index_data["total_size_bytes"] = sum(f.get("size_bytes", 0) for f in index_data["files"])
            self._save_index_locked(index_data)
            logger.info("Successfully added memory: %s -> %s", memory_id, summary)
            return unit

    def delete_memory(self, memory_id: str) -> bool:
        """Mark memory as deleted by ID."""
        lock = FileLock(self.lock_path)
        with lock:
            index_data = self._get_index_locked()
            found = False
            for file_info in index_data.get("files", []):
                filepath = self.memories_dir / file_info["filename"]
                if not filepath.exists():
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                except Exception:
                    continue

                for unit in file_data.get("memories", []):
                    if unit["id"] == memory_id:
                        if unit["status"] != "deleted":
                            unit["status"] = "deleted"
                            tz = datetime.datetime.now().astimezone().tzinfo
                            unit["updated_at"] = datetime.datetime.now(tz).replace(microsecond=0).isoformat()
                            index_data["active_memories"] = max(0, index_data.get("active_memories", 0) - 1)
                            index_data["deleted_memories"] = index_data.get("deleted_memories", 0) + 1
                            found = True
                            break
                
                if found:
                    # Write updated file back
                    temp_path = filepath.with_suffix(".tmp")
                    try:
                        with open(temp_path, "w", encoding="utf-8") as f:
                            json.dump(file_data, f, ensure_ascii=False, indent=2)
                        temp_path.replace(filepath)
                        file_info["size_bytes"] = filepath.stat().st_size
                    except Exception as e:
                        logger.error("Failed to write deleted memory file: %s", e)
                        if temp_path.exists():
                            temp_path.unlink()
                        return False
                    break

            if found:
                self._save_index_locked(index_data)
                logger.info("Successfully deleted memory %s", memory_id)
                return True
            return False

    def edit_memory(self, memory_id: str, summary: str = None, details: str = None) -> bool:
        """Edit an existing memory unit."""
        lock = FileLock(self.lock_path)
        with lock:
            index_data = self._get_index_locked()
            found = False
            for file_info in index_data.get("files", []):
                filepath = self.memories_dir / file_info["filename"]
                if not filepath.exists():
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                except Exception:
                    continue

                for unit in file_data.get("memories", []):
                    if unit["id"] == memory_id:
                        if summary is not None:
                            unit["summary"] = summary
                        if details is not None:
                            unit["details"] = details
                        tz = datetime.datetime.now().astimezone().tzinfo
                        unit["updated_at"] = datetime.datetime.now(tz).replace(microsecond=0).isoformat()
                        
                        if not self.validate_memory_unit(unit):
                            logger.error("Failed validation on edit memory %s", memory_id)
                            return False
                        found = True
                        break
                
                if found:
                    # Write updated file back
                    temp_path = filepath.with_suffix(".tmp")
                    try:
                        with open(temp_path, "w", encoding="utf-8") as f:
                            json.dump(file_data, f, ensure_ascii=False, indent=2)
                        temp_path.replace(filepath)
                        file_info["size_bytes"] = filepath.stat().st_size
                    except Exception as e:
                        logger.error("Failed to write edited memory file: %s", e)
                        if temp_path.exists():
                            temp_path.unlink()
                        return False
                    break

            if found:
                self._save_index_locked(index_data)
                logger.info("Successfully edited memory %s", memory_id)
                return True
            return False

    def list_memories(self) -> list[dict]:
        """List all active memories."""
        lock = FileLock(self.lock_path)
        active_units = []
        with lock:
            index_data = self._get_index_locked()
            for file_info in index_data.get("files", []):
                filepath = self.memories_dir / file_info["filename"]
                if not filepath.exists():
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                        for unit in file_data.get("memories", []):
                            if unit["status"] == "active":
                                active_units.append(unit)
                except Exception as e:
                    logger.error("Error reading memories from %s: %s", file_info["filename"], e)
        return active_units

    def extract_search_keywords(self, text: str) -> set[str]:
        """Simple alphanumeric keyword extractor from text."""
        # Convert to lowercase and find words >= 2 chars long
        words = re.findall(r"\b\w{2,}\b", text.lower())
        # Filter out common stop words if needed, but a simple set works well
        stop_words = {"what", "how", "why", "who", "when", "where", "this", "that", "them", "then", "there", "their", "have", "with", "from", "your", "does", "want"}
        return {w for w in words if w not in stop_words}

    def retrieve_memories(self, user_input: str, limit: int = 5) -> list[dict]:
        """Search and rank memories based on input query keywords overlap and recency."""
        if not self.enabled:
            return []

        search_keywords = self.extract_search_keywords(user_input)
        if not search_keywords:
            return []

        lock = FileLock(self.lock_path)
        candidate_units = []
        
        with lock:
            index_data = self._get_index_locked()
            # Sort files to load today and recent files first
            # Files sorted by name (YYYY-MM-DD_memory.json) desc
            files = sorted(index_data.get("files", []), key=lambda x: x["filename"], reverse=True)
            
            # Load active memories and score them
            for idx, file_info in enumerate(files):
                filepath = self.memories_dir / file_info["filename"]
                if not filepath.exists():
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                except Exception:
                    continue

                # Recency score based on file age index
                # Today and last 3 days get index 0, 1, 2, 3
                recency_weight = max(0.0, 1.0 - (idx * 0.15))

                for unit in file_data.get("memories", []):
                    if unit["status"] != "active" or unit.get("confidence", 1.0) < 0.60:
                        continue

                    # Keyword overlap count
                    overlap = len(search_keywords.intersection(set(unit["keywords"])))
                    if overlap == 0:
                        continue

                    # Scoring formula based on spec principle:
                    # score = overlap_count * 0.4 + recency_weight * 0.3 + confidence * 0.3
                    score = (overlap * 0.4) + (recency_weight * 0.3) + (unit.get("confidence", 0.5) * 0.3)
                    candidate_units.append((score, unit))

        # Sort candidate memories by score desc
        candidate_units.sort(key=lambda x: x[0], reverse=True)
        retrieved = [unit for _, unit in candidate_units[:limit]]
        
        logger.info("Retrieved %d memories for query keyword overlap: %s", len(retrieved), list(search_keywords))
        return retrieved

    def _call_ollama_json(self, messages: list[dict]) -> list[dict] | None:
        """Call Ollama and ensure a JSON array is returned."""
        import requests
        try:
            logger.info("Sending memory extraction task to Ollama (%s)", self.model)
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "format": "json"
                },
                timeout=90,
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            
            # Sanitise JSON
            cleaned = content.strip()
            # If Ollama wrapped JSON in standard markdown formatting, clean it
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)
                cleaned = cleaned.strip()

            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "memories" in data:
                return data["memories"]
            elif isinstance(data, dict):
                # Wrapped single object into array
                return [data]
        except Exception as e:
            logger.error("Failed to parse LLM response as JSON memories: %s", e)
        return None

    def start_background_extraction_phase_1(self, user_input: str) -> None:
        """Phase 1: On user input, start background thread to extract facts."""
        if not self.enabled:
            return
        thread = threading.Thread(target=self._run_extraction_phase_1, args=(user_input,), daemon=True)
        thread.start()

    def _run_extraction_phase_1(self, user_input: str) -> None:
        """Phase 1 thread target."""
        prompt = (
            "Analyze the user's message and extract any core facts worth remembering in a JSON format.\n"
            "Include user preferences, background profile, ongoing projects, skills, corrections, or todo items.\n"
            "Do NOT remember one-off small talk or speculative info.\n"
            "Format the output strictly as a JSON array where each item has:\n"
            "- 'category': one of ('profile', 'preference', 'project', 'todo', 'event', 'skill', 'correction', 'system')\n"
            "- 'keywords': 1 to 5 short keyword strings\n"
            "- 'summary': a concise one-sentence description of the fact\n"
            "- 'details': deeper details about it (can be empty string if summary is enough)\n"
            "- 'confidence': float between 0.0 and 1.0 (use 0.9-1.0 if stated explicitly, 0.7-0.89 if implied)\n\n"
            f"User input:\n\"{user_input}\"\n\nJSON output:"
        )
        
        messages = [
            {"role": "system", "content": "You are a memory extractor. Output JSON arrays only."},
            {"role": "user", "content": prompt}
        ]

        extracted = self._call_ollama_json(messages)
        if extracted:
            for item in extracted:
                try:
                    category = item.get("category", "project")
                    keywords = item.get("keywords", ["general"])
                    summary = item.get("summary", "")
                    details = item.get("details", "")
                    confidence = float(item.get("confidence", 0.8))
                    
                    if summary:
                        self.add_memory(category, keywords, summary, details, confidence, source="conversation")
                except Exception as e:
                    logger.error("Error saving extracted memory item from Phase 1: %s", e)

    def start_background_extraction_phase_2(self, user_input: str, assistant_response: str) -> None:
        """Phase 2: After AI response, extract commitments, facts, and conclusions."""
        if not self.enabled:
            return
        thread = threading.Thread(target=self._run_extraction_phase_2, args=(user_input, assistant_response), daemon=True)
        thread.start()

    def _run_extraction_phase_2(self, user_input: str, assistant_response: str) -> None:
        """Phase 2 thread target."""
        prompt = (
            "Analyze the conversation turn and extract any commitments, conclusions, or facts worth remembering in a JSON format.\n"
            "Focus on corrections made by the user, specific details mentioned, assistant commitments, or projects discussed.\n"
            "Format the output strictly as a JSON array where each item has:\n"
            "- 'category': one of ('profile', 'preference', 'project', 'todo', 'event', 'skill', 'correction', 'system')\n"
            "- 'keywords': 1 to 5 short keyword strings\n"
            "- 'summary': a concise one-sentence description of the fact/conclusion\n"
            "- 'details': deeper details about it\n"
            "- 'confidence': float between 0.0 and 1.0\n\n"
            f"User: \"{user_input}\"\nAssistant: \"{assistant_response}\"\n\nJSON output:"
        )

        messages = [
            {"role": "system", "content": "You are a memory extractor. Output JSON arrays only."},
            {"role": "user", "content": prompt}
        ]

        extracted = self._call_ollama_json(messages)
        if extracted:
            for item in extracted:
                try:
                    category = item.get("category", "project")
                    keywords = item.get("keywords", ["general"])
                    summary = item.get("summary", "")
                    details = item.get("details", "")
                    confidence = float(item.get("confidence", 0.8))

                    # De-duplicate: check if identical summary already in list_memories()
                    is_duplicate = False
                    for existing in self.list_memories():
                        if existing["summary"].lower() == summary.lower() or (existing["category"] == category and set(existing["keywords"]) == set(keywords) and existing["summary"] == summary):
                            is_duplicate = True
                            break

                    if summary and not is_duplicate:
                        self.add_memory(category, keywords, summary, details, confidence, source="conversation")
                except Exception as e:
                    logger.error("Error saving extracted memory item from Phase 2: %s", e)
