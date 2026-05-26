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
    print(f"\n{'='*50}")
    print(f"  Ann AI Assistant  v{version}")
    print(f"  Model: {config['llm']['model']}")
    print(f"{'='*50}")
    print("  Commands: 'exit' to quit | 'update' to update\n")

    evaluator = MoralEvaluator(BASE_DIR / "moral_module_spec.md")

    llm_model = config["llm"]["model"]
    llm_base_url = config["llm"].get("base_url", "http://localhost:11434")

    # --- Step 2: version check ---
    new_tag = check_for_update(config, BASE_DIR)
    if new_tag:
        print(f"Ann: New version {new_tag} is available.")
        answer = input("     Update now? (yes / later / skip): ").strip().lower()
        print()
        if answer in ("yes", "y"):
            sys.exit(EXIT_UPDATE)

    # --- Conversation loop ---
    conversation: list[dict] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAnn: Goodbye!")
            sys.exit(0)

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

        # Build the message for the LLM
        # For COMPLY_WITH_SAFEGUARDS, prepend a system note to guide the model
        if result.decision == Decision.COMPLY_WITH_SAFEGUARDS:
            llm_message = (
                f"[Important: {result.rationale} Respond carefully and include "
                f"appropriate disclaimers.]\n\nUser: {user_input}"
            )
        else:
            llm_message = user_input

        conversation.append({"role": "user", "content": llm_message})

        try:
            # Always inject the system prompt as the first message so Ann's
            # identity is established regardless of conversation history length.
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


if __name__ == "__main__":
    main()
