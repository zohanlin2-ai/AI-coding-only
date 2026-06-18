"""
Tests for the Document Q&A (RAG) module: DocumentStore + DocQAIntentParser.

Covers chunking boundaries (empty / oversized), retrieval via keyword fallback
and via embeddings, the loaded-document gate, and LLM-failure fault tolerance.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from doc_qa.document_store import DocumentStore
from doc_qa.doc_qa_handler import DocQAIntentParser


@pytest.fixture(autouse=True)
def _offline_embeddings(monkeypatch):
    """Fast-fail embedding HTTP calls so tests use the keyword fallback instantly."""
    import requests

    def _fail(*args, **kwargs):
        raise ConnectionError("offline in tests")

    monkeypatch.setattr(requests, "post", _fail)


def _store():
    # base_url unreachable in tests → embeddings fail → keyword fallback path.
    return DocumentStore("http://localhost:1", "test-model", max_chars=60)


# --- DocumentStore: chunking boundaries ------------------------------------

def test_empty_document_indexes_nothing():
    s = _store()
    assert s.add_document("doc", "") == 0
    assert s.add_document("doc", "   \n  ") == 0
    assert s.has_documents() is False


def test_chunking_splits_paragraphs():
    s = _store()
    text = "First paragraph about cats.\n\nSecond paragraph about dogs.\n\nThird about birds."
    n = s.add_document("animals", text)
    assert n >= 2
    assert s.has_documents() is True
    assert s.doc_names() == ["animals"]


def test_oversized_paragraph_is_hard_split():
    s = _store()  # max_chars=60
    long_para = "x" * 200  # single paragraph, no blank lines
    n = s.add_document("big", long_para)
    assert n >= 3  # 200 / 60 -> at least 4 chunks


def test_reindex_replaces_same_name():
    s = _store()
    s.add_document("doc", "alpha beta")
    s.add_document("doc", "gamma delta")
    hits = s.search("gamma")
    assert hits and "gamma" in hits[0][1]
    assert s.search("alpha") == []  # old content gone


# --- DocumentStore: retrieval ----------------------------------------------

def test_search_keyword_fallback_ranks_relevant_chunk():
    s = _store()
    s.add_document(
        "doc",
        "Photosynthesis converts sunlight into energy.\n\n"
        "The mitochondria is the powerhouse of the cell.\n\n"
        "Rivers flow into the ocean.",
    )
    hits = s.search("tell me about mitochondria")
    assert hits
    assert "mitochondria" in hits[0][1].lower()


def test_search_empty_store_and_empty_query():
    s = _store()
    assert s.search("anything") == []
    s.add_document("doc", "some content here")
    assert s.search("   ") == []


def test_search_no_overlap_returns_empty():
    s = _store()
    s.add_document("doc", "apples bananas cherries")
    assert s.search("xylophone zebra") == []


def test_search_uses_embeddings_when_available(monkeypatch):
    s = _store()
    # Deterministic fake embeddings: map text -> vector by keyword presence.
    def fake_embed(text):
        return [1.0, 0.0] if "cat" in text.lower() else [0.0, 1.0]
    monkeypatch.setattr(s, "_get_embedding", fake_embed)
    s.add_document("doc", "A story about a cat.\n\nA report on quarterly finance.")
    hits = s.search("cat behaviour")
    assert hits and "cat" in hits[0][1].lower()


# --- DocQAIntentParser: gating ---------------------------------------------

def test_parser_does_not_fire_without_documents():
    s = _store()
    parser = DocQAIntentParser("http://localhost:1", "m", s)
    assert parser.should_parse("summarize the document") is False  # no docs loaded


def test_parser_fires_with_documents_and_keyword():
    s = _store()
    s.add_document("doc", "content about taxes")
    parser = DocQAIntentParser("http://localhost:1", "m", s)
    assert parser.should_parse("summarize the document") is True
    assert parser.should_parse("what's the weather") is False  # no keyword


# --- DocQAIntentParser: execute --------------------------------------------

def _parser_with_doc():
    s = _store()
    s.add_document("doc", "The capital of France is Paris.\n\nThe Nile is in Egypt.")
    return DocQAIntentParser("http://localhost:1", "m", s), s


def test_execute_answers_from_excerpts():
    parser, store = _parser_with_doc()
    captured = {}

    def fake_llm(prompt):
        captured["prompt"] = prompt
        return "Paris."

    result = parser.execute({"query": "What is the capital of France?"},
                            {"call_llm": fake_llm, "document_store": store})
    assert result.reply == "Paris."
    assert "Paris" in captured["prompt"]  # excerpt was injected


def test_execute_no_relevant_passage():
    parser, store = _parser_with_doc()
    result = parser.execute({"query": "quantum chromodynamics xylophone"},
                            {"call_llm": lambda p: "x", "document_store": store})
    assert "couldn't find a relevant passage" in result.reply


def test_execute_llm_failure_is_graceful():
    parser, store = _parser_with_doc()

    def boom(prompt):
        raise RuntimeError("ollama down")

    result = parser.execute({"query": "capital of France"},
                            {"call_llm": boom, "document_store": store})
    assert "excerpts" in result.reply.lower()  # falls back to showing excerpts
    assert "Paris" in result.reply


def test_execute_no_llm_available():
    parser, store = _parser_with_doc()
    result = parser.execute({"query": "capital of France"},
                            {"call_llm": None, "document_store": store})
    assert "Paris" in result.reply
