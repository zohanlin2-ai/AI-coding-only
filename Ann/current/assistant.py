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
                    if "沒問題" in user_input_lower or "沒有問題" in user_input_lower:
                        intent = "yes"
                    elif any(w in user_input_lower for w in ["不要", "不", "否", "later", "no", "n", "暫時", "取消", "晚點", "拒絕", "skip", "先不要", "等一下", "等會", "待會", "下次", "沒空", "忙", "暫不", "以後", "不升", "沒興趣", "沒時間", "改天", "忽略"]):
                        intent = "no"
                    elif any(w in user_input_lower for w in ["好", "要", "更新", "ok", "yes", "y", "update", "sure", "確定", "可以", "對", "行", "同意", "升級", "安裝", "upgrade", "confirm", "現在", "即刻", "yer", "yeah", "yep", "yea"]):
                        intent = "yes"
                    else:
                        intent = "unknown"

                    if intent == "yes":
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
                from datetime import datetime
                parsed = intent_parser.parse_intent(user_input)
                if parsed["intent"] != "none":
                    intent = parsed["intent"]
                    reply = ""
                    if intent == "set_alarm":
                        time_str = parsed["time"]
                        label = parsed["label"]
                        repeat_pattern = parsed.get("repeat")
                        if not time_str:
                            reply = "請告訴我您想設定鬧鐘的具體時間。"
                        else:
                            try:
                                # Ollama's ISO format parsing
                                dt = datetime.fromisoformat(time_str)
                                success, msg_or_list, _ = alarm_manager.add_alarm(dt, label, repeat_pattern)
                                if success:
                                    repeat_msg = f" repeating '{repeat_pattern}'" if repeat_pattern else ""
                                    prompt = f"System instruction: The alarm was successfully set for {dt.strftime('%Y-%m-%d %H:%M')}{repeat_msg} with label '{label or '無'}'. Confirm this to the user in a friendly way."
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
                                f"- [ID: {a.id}] {a.datetime.strftime('%Y-%m-%d %H:%M:%S')} — {a.label or '無備註'}" +
                                (f" (重複: {a.repeat_pattern})" if a.repeat_pattern else "")
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
                        target_alarm = parsed["target_alarm"]
                        
                        try:
                            success, msg, matches = alarm_manager.delete_alarm_flow(
                                alarm_id=alarm_id,
                                target_alarm=target_alarm,
                                label=label
                            )
                            if not success and len(matches) > 1:
                                alarms_list = "\n".join(
                                    f"- [ID: {a.id}] {a.datetime.strftime('%Y-%m-%d %H:%M')} — {a.label or '無備註'}"
                                    for a in matches
                                )
                                prompt = (
                                    f"System instruction: Multiple alarms matched the deletion query. "
                                    f"Present the list of matching alarms below and ask the user to clarify which one they wish to delete by typing its ID (e.g. 'a1'):\n"
                                    f"{alarms_list}"
                                )
                                reply = call_ollama(llm_base_url, llm_model, [
                                    {"role": "system", "content": SYSTEM_PROMPT},
                                    {"role": "user", "content": prompt}
                                ])
                            elif success:
                                prompt = f"System instruction: {msg} Confirm this successful deletion to the user in a friendly way."
                                reply = call_ollama(llm_base_url, llm_model, [
                                    {"role": "system", "content": SYSTEM_PROMPT},
                                    {"role": "user", "content": prompt}
                                ])
                            else:
                                reply = msg
                        except Exception as ex:
                            reply = f"刪除鬧鐘時發生錯誤：{ex}"

                    elif intent == "update_alarm":
                        alarm_id = parsed["alarm_id"]
                        target_alarm = parsed["target_alarm"]
                        time_str = parsed["time"]
                        new_label = parsed["label"]
                        
                        dt = None
                        if time_str:
                            try:
                                dt = datetime.fromisoformat(time_str)
                            except Exception:
                                pass
                        
                        if not time_str and not new_label:
                            reply = "請告訴我您想將鬧鐘修改成什麼時間或什麼備註名稱。"
                        else:
                            try:
                                success, msg, matches = alarm_manager.update_alarm_flow(
                                    alarm_id=alarm_id,
                                    target_alarm=target_alarm,
                                    new_datetime=dt,
                                    new_label=new_label
                                )
                                if not success and len(matches) > 1:
                                    alarms_list = "\n".join(
                                        f"- [ID: {a.id}] {a.datetime.strftime('%Y-%m-%d %H:%M')} — {a.label or '無備註'}"
                                        for a in matches
                                    )
                                    prompt = (
                                        f"System instruction: Multiple alarms matched the update query. "
                                        f"Present the list of matching alarms below and ask the user to clarify which one they wish to update by typing its ID (e.g. 'a1'):\n"
                                        f"{alarms_list}"
                                    )
                                    reply = call_ollama(llm_base_url, llm_model, [
                                        {"role": "system", "content": SYSTEM_PROMPT},
                                        {"role": "user", "content": prompt}
                                    ])
                                elif success:
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
        assistant_gui.start_gui(config, evaluator, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser, new_tag)


if __name__ == "__main__":
    main()
