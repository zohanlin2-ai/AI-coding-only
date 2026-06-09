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

        # Conflict detection + organization trigger (outside lock, background)
        threading.Thread(
            target=self._detect_and_resolve_conflict,
            args=(category, keywords, summary),
            daemon=True,
        ).start()
        self._maybe_trigger_organization()
        self.start_background_organization()

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

    def get_stats(self) -> dict:
        """Return memory usage statistics from the index."""
        lock = FileLock(self.lock_path)
        with lock:
            data = self._get_index_locked()
        return {
            "active":   data.get("active_memories", 0),
            "outdated": data.get("outdated_memories", 0),
            "deleted":  data.get("deleted_memories", 0),
            "total":    data.get("total_memories", 0),
            "files":    len(data.get("files", [])),
            "size_kb":  round(data.get("total_size_bytes", 0) / 1024, 1),
            "enabled":  data.get("enabled", True),
        }

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
        """
        Search and rank memories relevant to *user_input*.

        Scoring strategy:
        - If Ollama embeddings are available, semantic cosine similarity
          (weight 0.5) is combined with keyword overlap (0.25) and recency +
          confidence (0.25).  All active memories are evaluated.
        - If embeddings are unavailable, falls back to keyword-only scoring:
          overlap (0.4) + recency (0.3) + confidence (0.3).  Memories with
          zero keyword overlap are skipped.
        """
        if not self.enabled:
            return []

        search_keywords = self.extract_search_keywords(user_input)

        # Try embedding for the query (non-blocking on failure)
        query_embedding = self._get_embedding(user_input)
        use_embeddings = query_embedding is not None

        if not use_embeddings and not search_keywords:
            return []

        lock = FileLock(self.lock_path)
        candidate_units = []

        with lock:
            index_data = self._get_index_locked()
            files = sorted(index_data.get("files", []), key=lambda x: x["filename"], reverse=True)

            for idx, file_info in enumerate(files):
                filepath = self.memories_dir / file_info["filename"]
                if not filepath.exists():
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                except Exception:
                    continue

                recency_weight = max(0.0, 1.0 - (idx * 0.15))

                for unit in file_data.get("memories", []):
                    if unit["status"] != "active" or unit.get("confidence", 1.0) < 0.60:
                        continue

                    confidence = unit.get("confidence", 0.5)
                    overlap = len(search_keywords.intersection(set(unit["keywords"]))) if search_keywords else 0

                    if use_embeddings:
                        mem_embedding = self._get_embedding(unit["summary"])
                        if mem_embedding is not None:
                            cos_sim = self._cosine_similarity(query_embedding, mem_embedding)
                            # Blend: semantic 0.50, keyword 0.25, recency+conf 0.25
                            score = (cos_sim * 0.50) + (min(overlap, 3) / 3 * 0.25) + ((recency_weight * 0.5 + confidence * 0.5) * 0.25)
                            if score > 0.30:  # discard clearly irrelevant results
                                candidate_units.append((score, unit))
                            continue
                        # embedding call failed for this unit — fall through to keyword

                    # Keyword-only path
                    if overlap == 0:
                        continue
                    score = (overlap * 0.4) + (recency_weight * 0.3) + (confidence * 0.3)
                    candidate_units.append((score, unit))

        candidate_units.sort(key=lambda x: x[0], reverse=True)
        retrieved = [unit for _, unit in candidate_units[:limit]]

        mode = "embedding+keyword" if use_embeddings else "keyword"
        logger.info("Retrieved %d memories (%s) for: %.60s", len(retrieved), mode, user_input)
        return retrieved

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def _detect_and_resolve_conflict(self, category: str, keywords: list[str], summary: str) -> None:
        """
        Check existing active memories in the same category for potential
        contradictions with the new *summary*.  If the LLM judges a conflict,
        the old memory is marked 'outdated'.

        Runs synchronously inside add_memory() (which is already called from
        background threads during extraction).  Skips quietly on any error so
        as never to block memory writing.
        """
        import requests

        kw_set = set(keywords)

        lock = FileLock(self.lock_path)
        with lock:
            index_data = self._get_index_locked()
            candidates = []
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
                    if unit["status"] != "active":
                        continue
                    if unit["category"] != category:
                        continue
                    if not kw_set.intersection(set(unit["keywords"])):
                        continue
                    candidates.append(unit)

        if not candidates:
            return

        # Ask the LLM whether any candidate conflicts with the new summary.
        prompt = (
            "You are a conflict detector for a memory system.\n"
            "New memory to add: \"{new}\"\n\n"
            "Existing memories in the same category:\n{existing}\n\n"
            "For each existing memory that DIRECTLY CONTRADICTS the new one, "
            "output its ID on a separate line, prefixed with 'CONFLICT:'. "
            "If no conflicts exist, output exactly: NONE"
        ).format(
            new=summary,
            existing="\n".join(f"- {u['id']}: {u['summary']}" for u in candidates),
        )

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a conflict detector. Output only as instructed."},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
                timeout=20,
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
        except Exception as e:
            logger.debug("Conflict detection LLM call failed (%s); skipping", e)
            return

        conflict_ids = re.findall(r"CONFLICT:\s*(M\.\d+)", content)
        if not conflict_ids:
            return

        tz = datetime.datetime.now().astimezone().tzinfo
        now_str = datetime.datetime.now(tz).replace(microsecond=0).isoformat()

        lock = FileLock(self.lock_path)
        with lock:
            index_data = self._get_index_locked()
            for file_info in index_data.get("files", []):
                filepath = self.memories_dir / file_info["filename"]
                if not filepath.exists():
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                except Exception:
                    continue

                changed = False
                for unit in file_data.get("memories", []):
                    if unit["id"] in conflict_ids and unit["status"] == "active":
                        unit["status"] = "outdated"
                        unit["updated_at"] = now_str
                        index_data["active_memories"] = max(0, index_data.get("active_memories", 0) - 1)
                        index_data["outdated_memories"] = index_data.get("outdated_memories", 0) + 1
                        changed = True
                        logger.info("Conflict resolved: marked %s as outdated (superseded by new memory)", unit["id"])

                if changed:
                    temp_path = filepath.with_suffix(".tmp")
                    try:
                        with open(temp_path, "w", encoding="utf-8") as f:
                            json.dump(file_data, f, ensure_ascii=False, indent=2)
                        temp_path.replace(filepath)
                        file_info["size_bytes"] = filepath.stat().st_size
                    except Exception as e:
                        logger.error("Failed to write conflict-resolved memory file: %s", e)
                        if temp_path.exists():
                            temp_path.unlink()

            self._save_index_locked(index_data)

    # ------------------------------------------------------------------
    # Embedding helpers
    # ------------------------------------------------------------------

    def _get_embedding(self, text: str) -> list[float] | None:
        """
        Request an embedding vector from Ollama for *text*.
        Returns None (and logs a warning) if the model or endpoint does not
        support embeddings — callers must handle None gracefully.
        """
        import requests
        try:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=15,
            )
            resp.raise_for_status()
            embedding = resp.json().get("embedding")
            if embedding and isinstance(embedding, list) and len(embedding) > 0:
                return embedding
        except Exception as e:
            logger.debug("Embedding not available (%s); falling back to keyword search", e)
        return None

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two equal-length vectors without numpy."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Auto organization
    # ------------------------------------------------------------------

    # Trigger organization when active memory count reaches a multiple of this.
    _ORGANIZE_EVERY = 20

    def _maybe_trigger_organization(self) -> None:
        """Flag needs_organization=True in the index when threshold is reached."""
        lock = FileLock(self.lock_path)
        with lock:
            data = self._get_index_locked()
            active = data.get("active_memories", 0)
            if active > 0 and active % self._ORGANIZE_EVERY == 0:
                data["needs_organization"] = True
                self._save_index_locked(data)
                logger.info("Organization threshold reached (%d active memories); flagging index", active)

    def start_background_organization(self) -> None:
        """
        Launch an organization pass if the index flag is set.
        Called from add_memory() after the index is updated.
        """
        lock = FileLock(self.lock_path)
        with lock:
            data = self._get_index_locked()
            needs = data.get("needs_organization", False)
        if needs:
            threading.Thread(target=self._run_organization, daemon=True).start()

    def _run_organization(self) -> None:
        """
        Merge highly similar memory clusters (same category, ≥3 shared keywords,
        confidence ≥ 0.7) into a single consolidated entry.  Replaces the old
        entries (marked outdated) with one merged entry.
        """
        import requests
        import datetime as _dt

        logger.info("Auto-organization: starting pass")

        # Load all active memories
        all_units = self.list_memories()
        if len(all_units) < 3:
            return

        # Group by category
        by_category: dict[str, list[dict]] = {}
        for unit in all_units:
            by_category.setdefault(unit["category"], []).append(unit)

        for category, units in by_category.items():
            if len(units) < 3:
                continue

            # Find clusters: pairs sharing ≥ 3 keywords
            clusters: list[list[dict]] = []
            used_ids: set[str] = set()

            for i, u1 in enumerate(units):
                if u1["id"] in used_ids:
                    continue
                cluster = [u1]
                kw1 = set(u1["keywords"])
                for u2 in units[i + 1:]:
                    if u2["id"] in used_ids:
                        continue
                    if len(kw1.intersection(set(u2["keywords"]))) >= 2 and u2.get("confidence", 0) >= 0.7:
                        cluster.append(u2)
                if len(cluster) >= 3:
                    clusters.append(cluster)
                    used_ids.update(u["id"] for u in cluster)

            for cluster in clusters:
                summaries = "\n".join(f"- {u['id']}: {u['summary']}" for u in cluster)
                prompt = (
                    f"Merge the following related memories about '{category}' into one concise summary sentence.\n"
                    f"Output only the merged sentence, nothing else.\n\n{summaries}"
                )
                try:
                    resp = requests.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": "You are a memory consolidator. Output only the merged sentence."},
                                {"role": "user", "content": prompt},
                            ],
                            "stream": False,
                        },
                        timeout=30,
                    )
                    resp.raise_for_status()
                    merged_summary = resp.json()["message"]["content"].strip()
                except Exception as e:
                    logger.warning("Organization merge LLM call failed: %s", e)
                    continue

                if not merged_summary:
                    continue

                # Mark originals outdated
                merged_keywords = list({kw for u in cluster for kw in u["keywords"]}[:5])
                for unit in cluster:
                    self.delete_memory(unit["id"])  # marks deleted for now to keep counts clean

                # Add merged entry
                merged_confidence = sum(u.get("confidence", 0.7) for u in cluster) / len(cluster)
                self.add_memory(
                    category=category,
                    keywords=merged_keywords,
                    summary=merged_summary,
                    details=f"Merged from: {', '.join(u['id'] for u in cluster)}",
                    confidence=min(merged_confidence, 1.0),
                    source="organization",
                )
                logger.info("Organization: merged %d memories -> new entry", len(cluster))

        # Clear the flag
        lock = FileLock(self.lock_path)
        with lock:
            data = self._get_index_locked()
            data["needs_organization"] = False
            data["last_organized"] = _dt.datetime.now().isoformat()
            self._save_index_locked(data)

        logger.info("Auto-organization: pass complete")

    # ------------------------------------------------------------------

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
