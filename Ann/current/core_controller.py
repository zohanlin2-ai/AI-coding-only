"""
core_controller.py — Unified business controller shared by CLI and GUI.

CoreController encapsulates all conversation business logic so that
assistant.py (CLI) and assistant_gui.py (GUI) become thin presentation
layers that simply call post_message() and render the result.

Responsibilities:
  - Moral evaluation (MoralEvaluator)
  - Memory retrieval and background extraction (MemoryManager)
  - Intent routing via IntentRouter (alarm, file, news, and future modules)
  - Fallback Ollama chat with vision routing for image attachments
  - Conversation history management

System commands (exit / restart / update / /memory) are intentionally NOT
handled here — they require immediate responses without LLM latency and must
be intercepted by the caller (CLI loop / GUI send_message) before
post_message() is invoked.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — single source of truth shared by CLI and GUI
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are Ann, a helpful, honest, and safety-conscious AI assistant. "
    "You were created by the Ann project and run locally on the user's machine. "
    "Never refer to yourself as Gemma, a language model, or any other product name. "
    "Your name is Ann and you should always introduce yourself as Ann. "
    "Respond in the same language the user writes in.\n"
    "When the user indicates they want to exit, close, or terminate the assistant program "
    "(e.g., 'close the window', 'shut down', 'exit', '再見', '關閉程式'), respond with a warm "
    "goodbye and append the marker '[EXIT]' at the very end of your response so the system "
    "can shut down.\n"
    "When the user indicates they want to restart the assistant program "
    "(e.g., 'restart', 'reboot', '重啟', '重新啟動'), respond with a warm response "
    "(e.g., 'I will restart now, see you in a moment!') and append the marker '[RESTART]' "
    "at the very end of your response so the system can restart.\n"
    "Security mode is handled automatically by the system — you do not need to append "
    "any marker for it yourself."
)


# Attachments larger than this are indexed into the DocumentStore for retrieval
# (RAG) instead of relying solely on the full-text dump into the prompt.
_DOC_INDEX_THRESHOLD = 1500

# ---------------------------------------------------------------------------
# ControllerResult — typed return value from post_message()
# ---------------------------------------------------------------------------

@dataclass
class ControllerResult:
    """
    Result object returned by CoreController.post_message().

    Attributes:
        reply:      The reply text to display to the user.
        is_refusal: True when the moral evaluator blocked the request.
        articles:   News article list for GUI card rendering (empty otherwise).
        marker:     Control marker stripped from LLM reply: '[EXIT]', '[RESTART]',
                    '[UPDATE]', '[MORAL_CONFIRM]', or None.
        error:      Non-empty string when an LLM/network error occurred.
        escalation_level: Moral escalation level E0–E5 (spec §19) when set.
    """
    reply: str
    is_refusal: bool = False
    articles: list = field(default_factory=list)
    marker: str | None = None
    error: str | None = None
    escalation_level: str | None = None


# ---------------------------------------------------------------------------
# /memory slash-command handler — shared by CLI and GUI
# ---------------------------------------------------------------------------

def handle_memory_command(user_input: str, memory_manager) -> str:
    """
    Processes a '/memory ...' slash command and returns the reply string.
    Both assistant.py (CLI) and assistant_gui.py (GUI) delegate to this function
    so the logic lives in exactly one place.
    """
    parts = user_input.split(maxsplit=2)
    cmd = parts[1].lower() if len(parts) > 1 else ""

    if cmd == "list":
        units = memory_manager.list_memories()
        if not units:
            return "目前沒有記錄任何記憶。"
        lines = ["我記住了以下內容："]
        for u in units:
            lines.append(
                f"• [{u['id']}] ({u['category']}) "
                f"(關鍵字: {', '.join(u['keywords'])}): {u['summary']}"
            )
        return "\n".join(lines)

    if cmd == "add":
        content = parts[2].strip() if len(parts) > 2 else ""
        if not content:
            return "請提供欲新增的記憶內容，例如: /memory add 喜歡喝黑咖啡"
        memory_manager.add_memory("profile", ["manual"], content, "", 1.0, source="manual")
        return "已成功手動新增記憶。"

    if cmd == "delete":
        mem_id = parts[2].strip() if len(parts) > 2 else ""
        if not mem_id:
            return "請指定要刪除的記憶 ID，例如: /memory delete M.1"
        success = memory_manager.delete_memory(mem_id)
        return f"已成功刪除記憶 {mem_id}。" if success else f"找不到記憶 {mem_id}。"

    if cmd == "edit":
        args = parts[2].strip().split(maxsplit=1) if len(parts) > 2 else []
        mem_id = args[0] if len(args) > 0 else ""
        new_summary = args[1] if len(args) > 1 else ""
        if not mem_id or not new_summary:
            return "請指定記憶 ID 與新內容，例如: /memory edit M.1 新的記憶內容"
        success = memory_manager.edit_memory(mem_id, summary=new_summary)
        return f"已成功編輯記憶 {mem_id}。" if success else f"找不到記憶 {mem_id}。"

    if cmd == "ui":
        return "Memory UI is only available in GUI mode. Launch Ann without --cli to use it."

    if cmd == "stats":
        s = memory_manager.get_stats()
        status = "開啟" if s["enabled"] else "關閉"
        return (
            f"📊 記憶統計\n"
            f"• 狀態: {status}\n"
            f"• 活躍記憶: {s['active']} 筆\n"
            f"• 已過期: {s['outdated']} 筆\n"
            f"• 已刪除: {s['deleted']} 筆\n"
            f"• 記憶檔案: {s['files']} 個\n"
            f"• 儲存大小: {s['size_kb']} KB"
        )

    if cmd == "off":
        memory_manager.toggle(False)
        return "記憶功能已關閉。"

    if cmd == "on":
        memory_manager.toggle(True)
        return "記憶功能已開啟。"

    return "未知的記憶指令。可用指令: /memory list | add | edit | delete | stats | ui | off | on"


# ---------------------------------------------------------------------------
# CoreController
# ---------------------------------------------------------------------------

class CoreController:
    """
    Unified conversation controller for Ann.

    Initialise once at startup, then call post_message() for every user turn.
    This method is thread-safe for single concurrent callers (CLI blocks; GUI
    dispatches to a single QThread worker at a time).
    """

    def __init__(self, config: dict, base_dir: Path) -> None:
        self.config = config
        self.base_dir = base_dir
        self.conversation: list[dict] = []

        llm_cfg = config["llm"]
        self.llm_base_url: str = llm_cfg.get("base_url", "http://localhost:11434")

        from ollama_client import OllamaClient
        self.ollama_client = OllamaClient(self.llm_base_url)

        # Resolve the effective model with graceful degradation:
        #   preferred (config) → first available → none (LLM-free command mode).
        # The resolved name is written back into the shared config dict so that
        # later config readers (SecurityDaemon, network monitor) use the same model.
        preferred_model: str = llm_cfg["model"]
        resolved_model = self.ollama_client.resolve_model(preferred_model)
        self.llm_available: bool = resolved_model is not None
        self.llm_model: str = resolved_model or preferred_model
        llm_cfg["model"] = self.llm_model

        from moral_evaluator import MoralEvaluator
        from moral_policy import load_policy
        self.evaluator = MoralEvaluator(base_dir / "moral_module_spec.md")
        self.moral_policy = load_policy(config)
        # Pending request awaiting user confirmation after an E1 moral escalation.
        self.pending_moral_action: dict | None = None

        from soul_manager import SoulManager
        self.soul_manager = SoulManager()

        from memory_manager import MemoryManager
        self.memory_manager = MemoryManager(
            base_dir=base_dir,
            base_url=self.llm_base_url,
            model=self.llm_model,
        )

        from intent_router import IntentRouter
        self.router = IntentRouter()

        # Alarm components — set via setup_alarm_components()
        self.alarm_manager = None

        # News manager — set inside setup_modules()
        self.news_manager = None

        # Document store (RAG) — set inside setup_modules()
        self.document_store = None

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def setup_modules(self) -> None:
        """Instantiate and register all feature modules into the router."""
        from pathlib import Path as _Path

        # ---- Alarm ----------------------------------------------------------
        from alarms.alarm_manager import AlarmManager
        from alarms.alarm_trigger import AlarmTrigger
        from alarms.alarm_scheduler import AlarmScheduler
        from alarms.intent_parser import IntentParser as AlarmIntentParser

        alarm_config = self.config.get("alarm", {})
        sound_filename = alarm_config.get("sound_path", "428157__setuniman__charade-1q62b.wav")
        sound_path = _Path(__file__).parent / sound_filename
        self.alarm_manager = AlarmManager()
        self.alarm_trigger = AlarmTrigger(sound_path=str(sound_path), volume=alarm_config.get("volume", 0.8))
        self.alarm_scheduler = AlarmScheduler(self.alarm_manager, self.alarm_trigger)
        self.router.register(AlarmIntentParser(self.llm_base_url, self.llm_model))

        # ---- File -----------------------------------------------------------
        from file_handler import FileIntentParser
        file_parser = FileIntentParser(self.llm_base_url, self.llm_model)
        self.router.register(file_parser)

        # ---- Document Q&A (RAG) — registered before news so it wins doc-
        #      questions ("summarize" etc.) only when a document is loaded -----
        from doc_qa.document_store import DocumentStore
        from doc_qa.doc_qa_handler import DocQAIntentParser
        self.document_store = DocumentStore(self.llm_base_url, self.llm_model)
        self.router.register(
            DocQAIntentParser(self.llm_base_url, self.llm_model, self.document_store)
        )

        from news.news_manager import NewsManager
        self.news_manager = NewsManager(
            base_dir=self.base_dir,
            base_url=self.llm_base_url,
            model=self.llm_model,
        )
        self.router.register(self.news_manager.intent_parser)

        from security_plugin import SecurityIntentParser
        self.router.register(SecurityIntentParser(self.llm_base_url, self.llm_model))

        from model_handler import ModelIntentParser
        self.router.register(ModelIntentParser(self.llm_base_url, self.llm_model))

    # ------------------------------------------------------------------
    # LLM helper (synchronous — call from a worker thread in GUI)
    # ------------------------------------------------------------------

    def call_llm(self, prompt: str) -> str:
        """
        Call Ollama with a single user prompt prepended by the system prompt.
        Used by module plugins (e.g. alarm) that need an LLM-generated reply.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return self.ollama_client.chat(self.llm_model, messages)

    # ------------------------------------------------------------------
    # Moral escalation + audit helpers (spec §19, §21)
    # ------------------------------------------------------------------

    def _moral_classify(self, prompt: str) -> str:
        """
        Dedicated LLM call for the moral risk classifier (spec §11.2).

        Deliberately bypasses the Ann persona SYSTEM_PROMPT (which would inject
        conversational tone and control markers like [EXIT]) so the classifier
        returns clean JSON.
        """
        messages = [
            {"role": "system", "content": "You are a strict safety risk classifier. "
                                          "Output only the requested JSON object, no prose."},
            {"role": "user", "content": prompt},
        ]
        return self.ollama_client.chat(self.llm_model, messages)

    def _write_audit(self, moral_result) -> None:
        """Append a redacted §21 audit record to logs/moral_audit.jsonl when present."""
        if not moral_result.audit_log:
            return
        try:
            log_dir = self.base_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            with open(log_dir / "moral_audit.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(moral_result.audit_log, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("Failed to write moral audit log: %s", exc)

    def resume_after_moral_confirm(self) -> ControllerResult:
        """
        Continue a request the user confirmed after an E1 moral escalation.
        Re-runs the pipeline with the moral gate already approved (safeguarded).
        """
        pending = self.pending_moral_action
        self.pending_moral_action = None
        if not pending:
            return ControllerResult(reply="There is no pending action to confirm.")
        return self.post_message(
            pending["user_text"],
            attachment_text=pending["attachment_text"],
            images=pending["images"],
            _approved_moral=pending["moral_result"],
        )

    def cancel_moral_confirm(self) -> None:
        """Discard a pending E1 escalation when the user declines."""
        self.pending_moral_action = None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def post_message(
        self,
        user_text: str,
        attachment_text: str = "",
        images: list | None = None,
        _approved_moral=None,
    ) -> ControllerResult:
        """
        Process one user message through the full pipeline and return a result.

        Pipeline:
          1. Moral evaluation
          2. Memory retrieval + Phase-1 background extraction
          3. Intent routing (alarm / file / news / ...)
          4. Fallback: general Ollama chat (with optional vision routing)
          5. Phase-2 background memory extraction

        This method blocks on Ollama calls.  In GUI mode, call it from a
        background QThread (ControllerWorker) so the UI stays responsive.

        Args:
            user_text:       Raw user input string.
            attachment_text: Pre-formatted text content of any attached files.
            images:          List of Path objects for image attachments.

        Returns:
            A ControllerResult describing the reply and any side-effects.
        """
        from moral_evaluator import Decision
        from alarm_handler import parse_reply_marker

        images = images or []

        # Update soul state
        self.soul_manager.update(user_text)

        # ---- 1. Moral evaluation (spec §9 pipeline) ---------------------
        if _approved_moral is not None:
            # User confirmed an earlier E1 escalation — proceed with safeguards.
            moral_result = _approved_moral
        else:
            moral_result = self.evaluator.evaluate(
                user_text,
                call_llm=self._moral_classify if self.llm_available else None,
                images=images,
                policy=self.moral_policy,
            )
            logger.info(
                "Moral eval | risk=%s decision=%s esc=%s confidence=%.2f | %r",
                moral_result.risk_level.value,
                moral_result.decision.value,
                moral_result.escalation_level,
                moral_result.confidence,
                user_text[:80],
            )
            self._write_audit(moral_result)

            if moral_result.decision == Decision.REFUSE:
                return ControllerResult(
                    reply=f"I'm unable to help with that. ({moral_result.rationale})",
                    is_refusal=True,
                    escalation_level=moral_result.escalation_level,
                )
            if moral_result.decision == Decision.PARTIAL_REFUSAL:
                return ControllerResult(
                    reply=f"⚠️ {moral_result.rationale}",
                    is_refusal=True,
                    escalation_level=moral_result.escalation_level,
                )
            if moral_result.decision == Decision.ESCALATE_OR_PAUSE:
                # E1 = pause for a yes/no user confirmation; other levels are advisory.
                if moral_result.escalation_level == "E1":
                    self.pending_moral_action = {
                        "user_text": user_text,
                        "attachment_text": attachment_text,
                        "images": images,
                        "moral_result": moral_result,
                    }
                    return ControllerResult(
                        reply=f"⚠️ {moral_result.rationale}\n\nDo you want to continue? (yes / no)",
                        marker="[MORAL_CONFIRM]",
                        escalation_level="E1",
                    )
                return ControllerResult(
                    reply=f"⚠️ {moral_result.rationale}",
                    is_refusal=True,
                    escalation_level=moral_result.escalation_level,
                )
            if moral_result.decision == Decision.CLARIFY:
                return ControllerResult(
                    reply=moral_result.rationale,
                    escalation_level=moral_result.escalation_level,
                )

        # ---- 2. Memory retrieval + Phase-1 extraction -------------------
        memories = self.memory_manager.retrieve_memories(user_text)
        self.memory_manager.start_background_extraction_phase_1(user_text)

        # ---- 3. Build context for module plugins ------------------------
        context: dict = {
            "config": self.config,
            "conversation": self.conversation,
            "base_dir": self.base_dir,
            "user_text": user_text,
            "call_llm": self.call_llm,
            "alarm_manager": self.alarm_manager,
            "news_manager": self.news_manager,
            "document_store": self.document_store,
            "controller": self,
        }

        # Index a large attachment for retrieval so DocQA can answer over it.
        # Small attachments are left to the normal full-dump path (unchanged).
        if self.document_store is not None and len(attachment_text) > _DOC_INDEX_THRESHOLD:
            self.document_store.add_document("attachment", attachment_text)

        # ---- 4. Intent routing ------------------------------------------
        module_result = self.router.route(user_text, context)
        if module_result is not None:
            clean_reply, marker = parse_reply_marker(module_result.reply)
            # Save to conversation history if there is a meaningful reply
            if clean_reply:
                self.conversation.append({"role": "user", "content": user_text})
                self.conversation.append({"role": "assistant", "content": clean_reply})
            return ControllerResult(
                reply=clean_reply,
                articles=module_result.data.get("articles", []),
                marker=marker or module_result.marker,
            )

        # ---- 5. Vision routing for image attachments --------------------
        target_model = self.llm_model
        if images:
            vision_model = self.ollama_client.find_first_vision_model()
            if vision_model:
                target_model = vision_model
                logger.info("Dynamic routing: using vision model %s", target_model)
            else:
                return ControllerResult(
                    reply=(
                        "⚠️ 偵測到您上傳了圖片，但本地未安裝任何支援視覺的模型。\n"
                        "請先在終端機執行 `ollama run llava` 下載並安裝視覺模型以進行分析。"
                    ),
                    is_refusal=True,
                )

        # ---- 6. Build LLM message ---------------------------------------
        # Apply safeguards for safeguarded requests and for user-confirmed escalations.
        apply_safeguards = (
            moral_result.decision == Decision.COMPLY_WITH_SAFEGUARDS
            or _approved_moral is not None
        )
        if apply_safeguards:
            extra = (" " + "; ".join(moral_result.safeguards)) if moral_result.safeguards else ""
            llm_message = (
                f"[Important: {moral_result.rationale}{extra} Respond carefully and include "
                f"appropriate disclaimers.]\n\nUser: {user_text}{attachment_text}"
            )
        else:
            llm_message = user_text + attachment_text

        self.conversation.append({"role": "user", "content": llm_message})

        # ---- 7. Build system prompt with injected memories and soul state --
        soul_instruction = self.soul_manager.get_system_instruction()
        base_prompt = f"{SYSTEM_PROMPT}{soul_instruction}"

        if memories:
            memory_str = "\n[Relevant Memory]\n" + "\n".join(
                f"{m['id']} [{m['category']}, {', '.join(m['keywords'])}] {m['summary']}"
                for m in memories
            )
            system_prompt = f"{base_prompt}\n{memory_str}"
        else:
            system_prompt = base_prompt

        messages_with_system = [
            {"role": "system", "content": system_prompt},
            *self.conversation,
        ]

        # ---- 8. Call Ollama ---------------------------------------------
        try:
            reply = self.ollama_client.chat(
                target_model,
                messages_with_system,
                images if images else None,
            )
        except Exception as exc:
            self.conversation.pop()  # don't store failed turn
            return ControllerResult(reply="", error=str(exc))

        clean_reply, marker = parse_reply_marker(reply)
        self.conversation.append({"role": "assistant", "content": clean_reply})

        # ---- 9. Phase-2 background memory extraction --------------------
        self.memory_manager.start_background_extraction_phase_2(user_text, clean_reply)

        return ControllerResult(reply=clean_reply, marker=marker)
