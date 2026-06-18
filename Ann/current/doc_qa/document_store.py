"""
DocumentStore — session-only chunk + embedding retrieval for attached documents.

Reuses the same embedding/cosine approach as the memory module (Ollama
`/api/embeddings`, no numpy) and degrades gracefully to keyword overlap when
embeddings are unavailable (Ollama offline or model without embedding support).

State is in-memory and resets on restart — documents are re-indexed when the
user attaches them again.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class DocumentStore:
    def __init__(self, base_url: str, model: str, max_chars: int = 800, top_k: int = 4) -> None:
        self.base_url = base_url
        self.model = model
        self.max_chars = max_chars
        self.top_k = top_k
        self._chunks: list[dict] = []  # {"name": str, "text": str, "embedding": list|None}

    # ------------------------------------------------------------------
    def add_document(self, name: str, text: str) -> int:
        """Chunk and index a document. Re-indexes if the same name already exists.
        Returns the number of chunks stored."""
        text = (text or "").strip()
        if not text:
            return 0
        self._chunks = [c for c in self._chunks if c["name"] != name]
        for chunk in self._chunk(text):
            self._chunks.append(
                {"name": name, "text": chunk, "embedding": self._get_embedding(chunk)}
            )
        return sum(1 for c in self._chunks if c["name"] == name)

    def _chunk(self, text: str) -> list[str]:
        """Split text into <= max_chars chunks on blank-line paragraph boundaries.
        Oversized paragraphs are hard-split by character count."""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            if len(para) > self.max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                for i in range(0, len(para), self.max_chars):
                    chunks.append(para[i : i + self.max_chars])
                continue
            if current and len(current) + len(para) + 2 > self.max_chars:
                chunks.append(current)
                current = para
            else:
                current = f"{current}\n\n{para}" if current else para
        if current:
            chunks.append(current)
        return chunks

    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int | None = None) -> list[tuple[str, str, float]]:
        """Return up to top_k (name, chunk, score) tuples ranked by relevance.
        Uses cosine similarity when embeddings exist, else keyword overlap."""
        top_k = top_k or self.top_k
        if not self._chunks or not query.strip():
            return []

        query_embedding = self._get_embedding(query)
        use_embeddings = bool(query_embedding) and any(c["embedding"] for c in self._chunks)

        scored: list[tuple[str, str, float]] = []
        for chunk in self._chunks:
            if use_embeddings and chunk["embedding"]:
                score = self._cosine(query_embedding, chunk["embedding"])
            else:
                score = self._keyword_overlap(query, chunk["text"])
            scored.append((chunk["name"], chunk["text"], score))

        scored.sort(key=lambda item: item[2], reverse=True)
        return [item for item in scored[:top_k] if item[2] > 0]

    def has_documents(self) -> bool:
        return bool(self._chunks)

    def doc_names(self) -> list[str]:
        return sorted({c["name"] for c in self._chunks})

    def clear(self) -> None:
        self._chunks = []

    # ------------------------------------------------------------------
    def _get_embedding(self, text: str) -> list[float] | None:
        """Best-effort embedding via Ollama. Returns None on any failure."""
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
            logger.debug("Doc embedding unavailable (%s); will use keyword fallback", e)
        return None

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _keyword_overlap(query: str, text: str) -> float:
        q_words = set(re.findall(r"\w+", query.lower()))
        if not q_words:
            return 0.0
        t_words = set(re.findall(r"\w+", text.lower()))
        return len(q_words & t_words) / len(q_words)
