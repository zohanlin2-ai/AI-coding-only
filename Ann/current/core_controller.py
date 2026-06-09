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
                    '[UPDATE]', or None.
        error:      Non-empty string when an LLM/network error occurred.
    """
    reply: str
    is_refusal: bool = False
    articles: list = field(default_factory=list)
    marker: str | None = None
    error: str | None = None


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

    if cmd == "off":
        memory_manager.toggle(False)
        return "記憶功能已關閉。"

    if cmd == "on":
        memory_manager.toggle(True)
        return "記憶功能已開啟。"

    return "未知的記憶指令。可用指令: /memory list | add | edit | delete | off | on"


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
        self.llm_model: str = llm_cfg["model"]

        from ollama_client import OllamaClient
        self.ollama_client = OllamaClient(self.llm_base_url)

        from moral_evaluator import MoralEvaluator
        self.evaluator = MoralEvaluator(base_dir / "moral_module_spec.md")

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
    # Main entry point
    # ------------------------------------------------------------------

    def post_message(
        self,
        user_text: str,
        attachment_text: str = "",
        images: list | None = None,
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

        # ---- 1. Moral evaluation ----------------------------------------
        moral_result = self.evaluator.evaluate(user_text)
        if moral_result.decision == Decision.REFUSE:
            return ControllerResult(
                reply=f"I'm unable to help with that. ({moral_result.rationale})",
                is_refusal=True,
            )
        if moral_result.decision == Decision.ESCALATE_OR_PAUSE:
            return ControllerResult(
                reply=f"⚠️ {moral_result.rationale}",
                is_refusal=True,
            )
        logger.info(
            "Moral eval | risk=%s decision=%s confidence=%.2f | %r",
            moral_result.risk_level.value,
            moral_result.decision.value,
            moral_result.confidence,
            user_text[:80],
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
            "controller": self,
        }

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
                articles=module_result.articles,
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
        if moral_result.decision == Decision.COMPLY_WITH_SAFEGUARDS:
            llm_message = (
                f"[Important: {moral_result.rationale} Respond carefully and include "
                f"appropriate disclaimers.]\n\nUser: {user_text}{attachment_text}"
            )
        else:
            llm_message = user_text + attachment_text

        self.conversation.append({"role": "user", "content": llm_message})

        # ---- 7. Build system prompt with injected memories --------------
        if memories:
            memory_str = "\n[Relevant Memory]\n" + "\n".join(
                f"{m['id']} [{m['category']}, {', '.join(m['keywords'])}] {m['summary']}"
                for m in memories
            )
            system_prompt = f"{SYSTEM_PROMPT}\n{memory_str}"
        else:
            system_prompt = SYSTEM_PROMPT

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
