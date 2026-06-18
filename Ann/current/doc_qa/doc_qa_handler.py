"""
DocQAIntentParser — answers questions over attached documents via retrieval.

Only fires when a document is loaded in the shared DocumentStore (so it never
intercepts normal chat or news/file requests when nothing is attached). Skips
the usual LLM intent-classification call: the gate is "a document is loaded and
the message references it", and the single LLM call happens in execute() to
answer from the retrieved excerpts.
"""
from __future__ import annotations

import logging

from base_intent_parser import BaseIntentParser, ModuleResult

logger = logging.getLogger(__name__)

DOC_QA_KEYWORDS = [
    "document", "doc", "pdf", "attached", "summarize", "summary", "explain this",
    "文件", "這份", "這個檔", "檔案", "總結", "摘要", "根據", "內容",
]


class DocQAIntentParser(BaseIntentParser):
    KEYWORDS = DOC_QA_KEYWORDS

    def __init__(self, base_url: str, model: str, store) -> None:
        super().__init__(base_url, model)
        self.store = store

    def should_parse(self, text: str) -> bool:
        # Gate on a loaded document so we never steal normal chat / news queries.
        return self.store.has_documents() and super().should_parse(text)

    def parse_intent(self, text: str) -> dict:
        if not self.should_parse(text):
            return self._empty_result()
        return {"intent": "ask_doc", "query": text}

    def _build_system_prompt(self) -> str:  # unused (parse_intent overridden)
        return ""

    def _validate_and_normalize(self, result: dict) -> dict:
        return result

    def _empty_result(self) -> dict:
        return {"intent": "none", "query": None}

    def _regex_fallback(self, text: str) -> dict:
        return {"intent": "ask_doc", "query": text}

    def execute(self, parsed: dict, context: dict) -> ModuleResult:
        store = context.get("document_store") or self.store
        query = parsed.get("query") or context.get("user_text", "")

        hits = store.search(query)
        if not hits:
            names = ", ".join(store.doc_names()) or "the document"
            return ModuleResult(
                reply=f"I have {names} loaded but couldn't find a relevant passage for that. "
                "Could you rephrase the question?"
            )

        excerpts = "\n\n---\n\n".join(f"[{name}] {chunk}" for name, chunk, _ in hits)
        prompt = (
            "Answer the question using ONLY the document excerpts below. If the answer is "
            "not contained in them, say you couldn't find it in the document.\n\n"
            f"Excerpts:\n{excerpts}\n\nQuestion: {query}"
        )

        call_llm = context.get("call_llm")
        if call_llm is None:
            return ModuleResult(reply=f"(No LLM available.) Relevant excerpts:\n\n{excerpts}")
        try:
            reply = call_llm(prompt)
        except Exception as e:
            logger.warning("DocQA LLM call failed: %s", e)
            return ModuleResult(
                reply=f"(Couldn't reach the LLM.) Relevant excerpts:\n\n{excerpts}"
            )
        return ModuleResult(reply=reply)
