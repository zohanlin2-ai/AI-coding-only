#!/usr/bin/env python3
"""
Ann — AI assistant core (CLI).

Startup sequence:
  1. Load config.yml
  2. Check GitHub for a newer release (if check_on_startup: true)
  3. If update available, ask user; exit(42) if they agree
  4. Build CoreController (handles moral eval, memory, intent routing, Ollama)
  5. Enter conversation loop

Exit codes:
  0  — clean exit (launcher will restart)
  3  — restart requested by user (launcher will restart immediately)
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

from alarm_handler import (  # noqa: E402
    UPDATE_CHECK_WORDS,
    UPDATE_CONFIRM_NO_REPLY,
    UPDATE_CONFIRM_UNCLEAR_REPLY,
    build_update_confirm_llm_message,
    detect_update_intent,
)
from core_controller import CoreController, ControllerResult, handle_memory_command, SYSTEM_PROMPT  # noqa: E402
from slash_commands import handle_slash_command  # noqa: E402
from version_check import check_for_update  # noqa: E402

EXIT_UPDATE = 42
EXIT_RESTART = 3

_EXIT_CMDS = {"exit", "close", "terminate", "close the window", "shut down", "再見", "關閉程式", "關閉"}
_RESTART_CMDS = {"restart", "reboot", "重啟", "重新啟動"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(BASE_DIR / "config.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    # ------------------------------------------------------------------
    # Self-test mode (used by updater.py post-swap validation)
    # ------------------------------------------------------------------
    if "--self-test" in sys.argv:
        try:
            load_config()
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
            # Verify new core modules can be imported
            import core_controller  # noqa: F401
            from intent_router import IntentRouter  # noqa: F401
            print("Self-test passed.")
            sys.exit(0)
        except Exception as e:
            print(f"Self-test failed: {e}", file=sys.stderr)
            sys.exit(1)

    config = load_config()
    setup_logging(config)

    version = (BASE_DIR / "version.txt").read_text(encoding="utf-8").strip()

    # Check for pygame availability
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("\n[Notice] pygame is not installed. Alarm audio notifications will be disabled.")
        print("         To enable sound, please run: pip install pygame\n")

    # Initialize Alarm components
    from alarms.alarm_manager import AlarmManager
    from alarms.alarm_trigger import AlarmTrigger
    from alarms.alarm_scheduler import AlarmScheduler
    from alarms.intent_parser import IntentParser as AlarmIntentParser

    alarm_config = config.get("alarm", {})
    sound_filename = alarm_config.get("sound_path", "428157__setuniman__charade-1q62b.wav")
    sound_path = CURRENT_DIR / sound_filename
    alarm_manager = AlarmManager()
    alarm_trigger = AlarmTrigger(sound_path=str(sound_path), volume=alarm_config.get("volume", 0.8))
    alarm_scheduler = AlarmScheduler(alarm_manager, alarm_trigger)
    alarm_intent_parser = AlarmIntentParser(
        base_url=config["llm"].get("base_url", "http://localhost:11434"),
        model=config["llm"]["model"],
    )

    # Build controller
    controller = CoreController(config, BASE_DIR)
    controller.setup_alarm_components(alarm_manager, alarm_trigger, alarm_scheduler, alarm_intent_parser)
    controller.setup_modules()

    # Start SecurityDaemon automatically
    from security_daemon import SecurityDaemon
    daemon = SecurityDaemon(config)
    daemon.start()

    # Version check
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

    try:
        if not has_qt:
            # ---- CLI mode ------------------------------------------------
            if not use_cli:
                print("\n[Notice] PyQt6 or PySide6 is not installed on this system.")
                print("         To enable the floating GUI interface, please run: pip install PyQt6")
            print(f"\n{'='*50}")
            print(f"  Ann AI Assistant (CLI)  v{version}")
            print(f"  Model: {config['llm']['model']}")
            print(f"{'='*50}")
            print("  Commands: 'exit' to quit | 'update' to update\n")

            awaiting_update_confirm = False
            pending_version: str | None = None
            security_mode = False

            if new_tag:
                awaiting_update_confirm = True
                pending_version = new_tag
                print(f"\nAnn: 偵測到新版本 {new_tag}。請問您現在需要更新嗎？[y/n]\n")

            def cli_alarm_callback(alarm):
                alarm_scheduler.active_triggered_alarms.append(alarm)
                alarm_trigger.play_sound()
                alarm_scheduler.start_cli_alerts(
                    alarm.label or "無備註",
                    alarm.datetime.strftime("%Y-%m-%d %H:%M"),
                )

            try:
                alarm_scheduler.start_cli_scheduler(cli_alarm_callback)

                while True:
                    try:
                        user_input = input("You: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nAnn: Goodbye!")
                        sys.exit(0)

                    # Dismiss triggered alarm
                    if alarm_scheduler.active_triggered_alarms:
                        alarm_trigger.stop_trigger()
                        alarm_scheduler.stop_cli_alerts()
                        alarm_scheduler.active_triggered_alarms.clear()
                        print("\nAnn: 鬧鐘已關閉。\n")
                        continue

                    if not user_input:
                        continue

                    user_lower = user_input.lower().strip()

                    # ---- /memory slash commands (fast, no LLM) --------------
                    if user_lower.startswith("/memory"):
                        reply = handle_memory_command(user_input, controller.memory_manager)
                        print(f"\nAnn: {reply}\n")
                        continue

                    # ---- Slash commands (fast, no LLM) ----------------------
                    slash_result = handle_slash_command(user_input, controller, BASE_DIR)
                    if slash_result.handled:
                        print(f"\nAnn: {slash_result.reply}\n")
                        continue

                    # ---- System commands ------------------------------------
                    if user_lower in _EXIT_CMDS:
                        print("\nAnn: 再見！有需要隨時找我。\n")
                        sys.exit(0)

                    if user_lower in _RESTART_CMDS:
                        print("\nAnn: 好的，我現在重新啟動，稍後見！\n")
                        sys.exit(EXIT_RESTART)

                    # ---- Update confirmation flow ----------------------------
                    if awaiting_update_confirm:
                        intent = detect_update_intent(user_lower) if user_lower != "/y" else "yes"
                        if intent == "yes":
                            if security_mode:
                                awaiting_update_confirm = False
                                pending_version = None
                                print("\nAnn: 安全模式下無法進行更新。請先關閉安全模式。\n")
                                continue
                            if daemon.running:
                                print("\nAnn: 偵測到安全監控 Daemon 正在執行，正在先將其關閉...")
                                daemon.stop()
                            awaiting_update_confirm = False
                            llm_msg = build_update_confirm_llm_message(pending_version, user_input)
                            controller.conversation.append({"role": "user", "content": llm_msg})
                            pending_version = None
                            try:
                                messages = [
                                    {"role": "system", "content": SYSTEM_PROMPT},
                                    *controller.conversation,
                                ]
                                reply = controller.ollama_client.chat(controller.llm_model, messages)
                                clean = reply.replace("[UPDATE]", "").strip()
                                controller.conversation.append({"role": "assistant", "content": clean})
                                print(f"\nAnn: {clean}\n")
                            except Exception:
                                print("\nAnn: 好的，即將進行更新並重新啟動應用程式...\n")
                            sys.exit(EXIT_UPDATE)
                        elif intent == "no":
                            awaiting_update_confirm = False
                            pending_version = None
                            print(f"\nAnn: {UPDATE_CONFIRM_NO_REPLY}\n")
                        else:
                            print(f"\nAnn: {UPDATE_CONFIRM_UNCLEAR_REPLY}\n")
                        continue

                    # ---- On-demand update check -----------------------------
                    if user_lower == "/update" or any(w in user_lower for w in UPDATE_CHECK_WORDS):
                        if security_mode:
                            print("\nAnn: 安全模式下無法進行更新。請先關閉安全模式。\n")
                            continue
                        print("\nAnn: 正在檢查更新，請稍候...")
                        new_version = check_for_update(config, BASE_DIR)
                        if new_version:
                            awaiting_update_confirm = True
                            pending_version = new_version
                            print(f"\nAnn: 偵測到新版本 {new_version}。請問您現在要更新嗎？[y/n]\n")
                        else:
                            print("\nAnn: 您目前已是最新版本，不需要更新。\n")
                        continue

                    # ---- Normal message → CoreController --------------------
                    daemon.pause()
                    try:
                        result: ControllerResult = controller.post_message(user_input)
                    finally:
                        daemon.resume()

                    if result.error:
                        print(f"\nAnn: (LLM error — is Ollama running? {result.error})\n")
                        continue

                    print(f"\nAnn: {result.reply}\n")

                    if result.marker == "[EXIT]":
                        sys.exit(0)
                    elif result.marker == "[RESTART]":
                        sys.exit(EXIT_RESTART)
                    elif result.marker == "[UPDATE]":
                        sys.exit(EXIT_UPDATE)
                    elif result.marker == "[SECURITY_ON]":
                        security_mode = True
                    elif result.marker == "[SECURITY_OFF]":
                        security_mode = False

            finally:
                alarm_scheduler.stop_cli_scheduler()
                alarm_trigger.stop_trigger()

        else:
            # ---- GUI mode -----------------------------------------------
            import assistant_gui
            assistant_gui.start_gui(
                config,
                controller,
                alarm_manager,
                alarm_trigger,
                alarm_scheduler,
                new_tag,
            )
    finally:
        daemon.stop()


if __name__ == "__main__":
    main()
