#!/usr/bin/env python3
"""
Ann — AI assistant core (CLI).

Startup sequence:
  1. Load config.yml
  2. Check GitHub for a newer release (if check_on_startup: true)
  3. If update available, ask user; exit(42) if they agree
  4. Enter conversation loop backed by Ollama (gemma4:e4b by default)
  5. Every user message is evaluated by MoralEvaluator before reaching the LLM

Exit codes:
  0  — clean exit (launcher will restart)
  42 — update requested by user (launcher will run updater)
"""
import logging
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Path setup — current/ lives inside the Ann root
# ---------------------------------------------------------------------------
CURRENT_DIR = Path(__file__).parent
BASE_DIR = CURRENT_DIR.parent

sys.path.insert(0, str(CURRENT_DIR))

from alarm_handler import detect_update_intent, handle_alarm_intent  # noqa: E402
from moral_evaluator import Decision, MoralEvaluator  # noqa: E402
from version_check import check_for_update  # noqa: E402

EXIT_UPDATE = 42
EXIT_RESTART = 3

# ---------------------------------------------------------------------------
# System prompt — establishes Ann's identity for every conversation.
# The underlying model (e.g. gemma4:e4b) must never reveal its own name;
# it always presents itself as Ann.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are Ann, a helpful, honest, and safety-conscious AI assistant. "
    "You were created by the Ann project and run locally on the user's machine. "
    "Never refer to yourself as Gemma, a language model, or any other product name. "
    "Your name is Ann and you should always introduce yourself as Ann. "
    "Respond in the same language the user writes in.\n"
    "When the user indicates they want to exit, close, or terminate the assistant program (e.g., 'close the window', 'shut down', 'exit', '再見', '關閉程式'), respond with a warm goodbye and append the marker '[EXIT]' at the very end of your response so the system can shut down.\n"
    "When the user indicates they want to restart the assistant program (e.g., 'restart', 'reboot', '重啟', '重新啟動'), respond with a warm response (e.g., 'I will restart now, see you in a moment!') and append the marker '[RESTART]' at the very end of your response so the system can restart.\n"
    "When the user indicates they want to update the assistant program (e.g., 'update', 'upgrade', '更新', '升級'), respond with a warm response confirming the update and append the marker '[UPDATE]' at the very end of your response so the system can perform the update."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_config() -> dict:
    with open(BASE_DIR / "config.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def call_ollama(base_url: str, model: str, messages: list[dict]) -> str:
    """Send a chat request to the local Ollama server and return the reply."""
    from ollama_client import OllamaClient
    client = OllamaClient(base_url)
    return client.chat(model, messages)


def setup_logging(config: dict) -> None:
    level = config.get("logging", {}).get("level", "INFO")
    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)
    from datetime import datetime

    log_file = logs_dir / f"assistant_{datetime.now():%Y%m%d}.log"
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if "--self-test" in sys.argv:
        try:
            # 1. Load config
            load_config()
            # 2. Check UI framework import if GUI mode
            use_cli = "--cli" in sys.argv
            if not use_cli:
                try:
                    import PyQt6  # noqa: F401
                    has_qt = True
                except ImportError:
                    try:
                        import PySide6  # noqa: F401
                        has_qt = True
                    except ImportError:
                        has_qt = False
                
                if has_qt:
                    import assistant_gui  # noqa: F401
            print("Self-test passed.")
            sys.exit(0)
        except Exception as e:
            print(f"Self-test failed: {e}", file=sys.stderr)
            sys.exit(1)

    config = load_config()
    setup_logging(config)

    version = (BASE_DIR / "version.txt").read_text(encoding="utf-8").strip()
    evaluator = MoralEvaluator(BASE_DIR / "moral_module_spec.md")

    # Check for pygame availability on startup
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("\n[Notice] pygame is not installed. Alarm audio notifications will be disabled.")
        print("         To enable sound, please run: pip install pygame\n")

    # Initialize Alarm components
    from alarms.alarm_manager import AlarmManager
    from alarms.alarm_trigger import AlarmTrigger
    from alarms.alarm_scheduler import AlarmScheduler
    from alarms.intent_parser import IntentParser

    alarm_config = config.get("alarm", {})
    sound_filename = alarm_config.get("sound_path", "428157__setuniman__charade-1q62b.wav")
    sound_path = CURRENT_DIR / sound_filename
    alarm_manager = AlarmManager()
    alarm_trigger = AlarmTrigger(sound_path=str(sound_path), volume=alarm_config.get("volume", 0.8))
    alarm_scheduler = AlarmScheduler(alarm_manager, alarm_trigger)
    intent_parser = IntentParser(
        base_url=config["llm"].get("base_url", "http://localhost:11434"),
        model=config["llm"]["model"]
    )
    from file_handler import FileIntentParser
    file_intent_parser = FileIntentParser(
        base_url=config["llm"].get("base_url", "http://localhost:11434"),
        model=config["llm"]["model"]
    )

    # --- Step 2: version check ---
    new_tag = check_for_update(config, BASE_DIR)

    # Mode determination
    use_cli = "--cli" in sys.argv
    has_qt = False
    if not use_cli:
        try:
            import PyQt6  # noqa: F401
            has_qt = True
        except ImportError:
            try:
                import PySide6  # noqa: F401
                has_qt = True
            except ImportError:
                has_qt = False

    # Startup blocking updates removed in favor of conversational updates.

    if not has_qt:
        # Run CLI loop
        if not use_cli:
            print("\n[Notice] PyQt6 or PySide6 is not installed on this system.")
            print("         To enable the floating GUI interface, please run: pip install PyQt6")
        print(f"\n{'='*50}")
        print(f"  Ann AI Assistant (CLI)  v{version}")
        print(f"  Model: {config['llm']['model']}")
        print(f"{'='*50}")
        print("  Commands: 'exit' to quit | 'update' to update\n")

        llm_model = config["llm"]["model"]
        llm_base_url = config["llm"].get("base_url", "http://localhost:11434")

        # --- CLI Conversation loop ---
        conversation: list[dict] = []
        awaiting_update_confirm = False
        pending_version = None
        if new_tag:
            awaiting_update_confirm = True
            pending_version = new_tag
            print(f"\nAnn: 偵測到新版本 {new_tag}。請問您現在需要更新嗎？[y/n]\n")
        
        def cli_alarm_callback(alarm):
            alarm_scheduler.active_triggered_alarms.append(alarm)
            alarm_trigger.play_sound()
            alarm_scheduler.start_cli_alerts(alarm.label or "無備註", alarm.datetime.strftime("%Y-%m-%d %H:%M"))

        try:
            alarm_scheduler.start_cli_scheduler(cli_alarm_callback)
            while True:
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nAnn: Goodbye!")
                    sys.exit(0)

                if alarm_scheduler.active_triggered_alarms:
                    # Dismiss triggered alarms
                    alarm_trigger.stop_trigger()
                    alarm_scheduler.stop_cli_alerts()
                    alarm_scheduler.active_triggered_alarms.clear()
                    print("\nAnn: 鬧鐘已關閉。\n")
                    continue

                if not user_input:
                    continue

                if user_input.lower() == "exit":
                    print("Ann: Goodbye!")
                    sys.exit(0)

                user_input_lower = user_input.lower().strip()
                if awaiting_update_confirm:
                    intent = detect_update_intent(user_input_lower)

                    if intent == "yes":
                        llm_message = (
                            f"[System Instruction: The user confirmed they want to install the available update (version {pending_version}). "
                            f"Reply with a warm goodbye and state that you are starting the update. "
                            f"You MUST append the marker '[UPDATE]' at the very end of your response so the system can run the updater.]\n\n"
                            f"User: {user_input}"
                        )
                        conversation.append({"role": "user", "content": llm_message})
                        awaiting_update_confirm = False
                        pending_version = None
                        
                        try:
                            messages_with_system = [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                *conversation,
                            ]
                            reply = call_ollama(llm_base_url, llm_model, messages_with_system)
                            clean_reply = reply.replace("[UPDATE]", "").strip()
                            conversation.append({"role": "assistant", "content": clean_reply})
                            print(f"\nAnn: {clean_reply}\n")
                        except Exception as e:
                            print("\nAnn: 好的，即將進行更新並重新啟動應用程式...\n")
                        sys.exit(EXIT_UPDATE)
                    elif intent == "no":
                        awaiting_update_confirm = False
                        pending_version = None
                        print("\nAnn: 好的，那我們先不更新。如果您想再次檢查，可以隨時對我說『更新』。\n")
                    else:
                        print("\nAnn: 我不太確定您的意思。請問您現在需要更新程式嗎？[y/n]\n")
                    continue

                # Intercept update check requests
                if any(w in user_input_lower for w in ["update", "更新", "檢查更新", "升級", "check update"]):
                    print("\nAnn: 正在檢查更新，請稍候...")
                    new_version = check_for_update(config, BASE_DIR)
                    if new_version:
                        awaiting_update_confirm = True
                        pending_version = new_version
                        print(f"\nAnn: 偵測到新版本 {new_version}。請問您現在要更新嗎？[y/n]\n")
                    else:
                        print("\nAnn: 您目前已是最新版本，不需要更新。\n")
                    continue

                # --- Moral evaluation (every message, no exceptions) ---
                result = evaluator.evaluate(user_input)
                logging.info(
                    "Moral eval | risk=%s decision=%s confidence=%.2f | %r",
                    result.risk_level.value,
                    result.decision.value,
                    result.confidence,
                    user_input[:80],
                )

                if result.decision == Decision.REFUSE:
                    print(f"\nAnn: I'm unable to help with that.\n     ({result.rationale})\n")
                    continue

                if result.decision == Decision.ESCALATE_OR_PAUSE:
                    print(f"\nAnn: ⚠️  {result.rationale}\n")
                    continue

                # --- Alarm Intent Handling ---
                parsed = intent_parser.parse_intent(user_input)
                def _cli_call_llm(prompt: str) -> str:
                    return call_ollama(llm_base_url, llm_model, [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ])
                reply = handle_alarm_intent(parsed, alarm_manager, _cli_call_llm)
                if reply is not None:
                    print(f"\nAnn: {reply}\n")
                    continue
                # --- File Intent Handling ---
                file_parsed = file_intent_parser.parse_intent(user_input)
                if file_parsed["intent"] != "none":
                    from file_handler import handle_file_intent
                    file_reply = handle_file_intent(file_parsed, conversation, BASE_DIR)
                    if file_reply is not None:
                        print(f"\nAnn: {file_reply}\n")
                        continue
                # Build the message for the LLM
                if result.decision == Decision.COMPLY_WITH_SAFEGUARDS:
                    llm_message = (
                        f"[Important: {result.rationale} Respond carefully and include "
                        f"appropriate disclaimers.]\n\nUser: {user_input}"
                    )
                else:
                    llm_message = user_input

                conversation.append({"role": "user", "content": llm_message})

                try:
                    messages_with_system = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        *conversation,
                    ]
                    reply = call_ollama(llm_base_url, llm_model, messages_with_system)
                except Exception as e:
                    print(f"\nAnn: (LLM error — is Ollama running? {e})\n")
                    conversation.pop()  # don't store failed turn
                    continue

                if "[EXIT]" in reply:
                    clean_reply = reply.replace("[EXIT]", "").strip()
                    conversation.append({"role": "assistant", "content": clean_reply})
                    print(f"\nAnn: {clean_reply}\n")
                    sys.exit(0)
                elif "[RESTART]" in reply:
                    clean_reply = reply.replace("[RESTART]", "").strip()
                    conversation.append({"role": "assistant", "content": clean_reply})
                    print(f"\nAnn: {clean_reply}\n")
                    sys.exit(EXIT_RESTART)
                elif "[UPDATE]" in reply:
                    clean_reply = reply.replace("[UPDATE]", "").strip()
                    conversation.append({"role": "assistant", "content": clean_reply})
                    print(f"\nAnn: {clean_reply}\n")
                    sys.exit(EXIT_UPDATE)
                else:
                    conversation.append({"role": "assistant", "content": reply})
                    print(f"\nAnn: {reply}\n")
        finally:
            alarm_scheduler.stop_cli_scheduler()
            alarm_trigger.stop_trigger()
    else:
        # Run GUI loop
        import assistant_gui
        assistant_gui.start_gui(config, evaluator, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser, new_tag)


if __name__ == "__main__":
    main()
