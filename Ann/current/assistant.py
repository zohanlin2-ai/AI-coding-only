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

from moral_evaluator import Decision, MoralEvaluator  # noqa: E402
from version_check import check_for_update  # noqa: E402

EXIT_UPDATE = 42

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
    "Respond in the same language the user writes in."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_config() -> dict:
    with open(BASE_DIR / "config.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def call_ollama(base_url: str, model: str, messages: list[dict]) -> str:
    """Send a chat request to the local Ollama server and return the reply."""
    import requests

    resp = requests.post(
        f"{base_url}/api/chat",
        json={"model": model, "messages": messages, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


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

    if new_tag:
        if not has_qt:
            print(f"\nAnn: New version {new_tag} is available.")
            answer = input("     Update now? (yes / later / skip): ").strip().lower()
            print()
            if answer in ("yes", "y"):
                sys.exit(EXIT_UPDATE)
        else:
            # Ask via QMessageBox using available Qt library
            try:
                from PyQt6.QtWidgets import QApplication, QMessageBox
            except ImportError:
                from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication(sys.argv)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText(f"New version {new_tag} is available.")
            msg.setWindowTitle("Ann Update")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            msg.button(QMessageBox.StandardButton.No).setText("Later")

            retval = msg.exec()
            if retval == QMessageBox.StandardButton.Yes:
                sys.exit(EXIT_UPDATE)
            app.quit()

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

                if user_input.lower() == "update":
                    sys.exit(EXIT_UPDATE)

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
                from datetime import datetime
                parsed = intent_parser.parse_intent(user_input)
                if parsed["intent"] != "none":
                    intent = parsed["intent"]
                    reply = ""
                    if intent == "set_alarm":
                        time_str = parsed["time"]
                        label = parsed["label"]
                        if not time_str:
                            reply = "請告訴我您想設定鬧鐘的具體時間。"
                        else:
                            try:
                                # Ollama's ISO format parsing
                                dt = datetime.fromisoformat(time_str)
                                success, msg_or_list, _ = alarm_manager.add_alarm(dt, label)
                                if success:
                                    prompt = f"System instruction: The alarm was successfully set for {dt.strftime('%Y-%m-%d %H:%M')} with label '{label or '無'}'. Confirm this to the user in a friendly way."
                                    reply = call_ollama(llm_base_url, llm_model, [
                                        {"role": "system", "content": SYSTEM_PROMPT},
                                        {"role": "user", "content": prompt}
                                    ])
                                else:
                                    limit_prompt = (
                                        f"System instruction: The user wants to set an alarm but the limit of 10 active alarms has been reached.\n"
                                        f"Here is the list of active alarms:\n{msg_or_list}\n"
                                        f"Please inform the user about the limit and present this list of current alarms with their IDs, asking which one they would like to delete to make room."
                                    )
                                    reply = call_ollama(llm_base_url, llm_model, [
                                        {"role": "system", "content": SYSTEM_PROMPT},
                                        {"role": "user", "content": limit_prompt}
                                    ])
                            except Exception as ex:
                                reply = f"設定鬧鐘時發生錯誤：{ex}"
                                
                    elif intent == "list_alarms":
                        alarms = alarm_manager.get_alarms()
                        if not alarms:
                            reply = "您目前沒有設定 any 鬧鐘。"
                        else:
                            alarms_list = "\n".join(
                                f"- [ID: {a.id}] {a.datetime.strftime('%Y-%m-%d %H:%M:%S')} — {a.label or '無備註'}"
                                for a in alarms
                            )
                            format_prompt = (
                                f"System instruction: Present the following active alarms list to the user in a friendly way:\n{alarms_list}"
                            )
                            reply = call_ollama(llm_base_url, llm_model, [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": format_prompt}
                            ])
                            
                    elif intent == "delete_alarm":
                        alarm_id = parsed["alarm_id"]
                        label = parsed["label"]
                        deleted = False
                        if alarm_id:
                            deleted = alarm_manager.delete_alarm(alarm_id)
                        elif label:
                            deleted = alarm_manager.delete_alarm_by_label(label)
                        
                        if deleted:
                            prompt = f"System instruction: The alarm (ID/label: {alarm_id or label}) has been successfully deleted. Confirm this to the user in a friendly way."
                            reply = call_ollama(llm_base_url, llm_model, [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": prompt}
                            ])
                        else:
                            reply = f"找不到符合條件的鬧鐘（ID: {alarm_id or '無'}, 標籤: {label or '無'}），請確認後再試。"

                    elif intent == "update_alarm":
                        alarm_id = parsed["alarm_id"]
                        target_alarm = parsed["target_alarm"]
                        time_str = parsed["time"]
                        if not time_str:
                            reply = "請告訴我您想將鬧鐘修改成什麼時間。"
                        else:
                            try:
                                dt = datetime.fromisoformat(time_str)
                                success, msg = alarm_manager.update_alarm(
                                    alarm_id=alarm_id, 
                                    target_alarm=target_alarm, 
                                    new_datetime=dt
                                )
                                if success:
                                    prompt = f"System instruction: {msg} Confirm this successful update to the user in a friendly way."
                                    reply = call_ollama(llm_base_url, llm_model, [
                                        {"role": "system", "content": SYSTEM_PROMPT},
                                        {"role": "user", "content": prompt}
                                    ])
                                else:
                                    reply = msg
                            except Exception as ex:
                                reply = f"修改鬧鐘時發生錯誤：{ex}"

                    print(f"\nAnn: {reply}\n")
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

                conversation.append({"role": "assistant", "content": reply})
                print(f"\nAnn: {reply}\n")
        finally:
            alarm_scheduler.stop_cli_scheduler()
            alarm_trigger.stop_trigger()
    else:
        # Run GUI loop
        import assistant_gui
        assistant_gui.start_gui(config, evaluator, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser)


if __name__ == "__main__":
    main()
