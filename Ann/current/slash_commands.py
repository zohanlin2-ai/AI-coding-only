"""
slash_commands.py — Stateless slash command handler shared by CLI and GUI.

Handled here (no LLM, no state):
  /help     — list all available slash commands
  /version  — show local Ann version (reads version.txt)
  /model    — show current LLM model
  /models   — list all installed Ollama models
  /switch   — switch to a different LLM model

NOT handled here (require UI state or exit codes):
  /update   — triggers update check flow (managed by CLI/GUI)
  /y        — confirms a pending /update (managed by CLI/GUI)
  /memory   — managed by handle_memory_command() in core_controller.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SlashResult:
    handled: bool
    reply: str = ""


def handle_slash_command(user_input: str, controller, base_dir: Path) -> SlashResult:
    """
    Try to handle user_input as a slash command.
    Returns SlashResult(handled=True) if it was a slash command, False otherwise.
    """
    text = user_input.strip()
    lower = text.lower()

    if lower == "/help":
        return SlashResult(handled=True, reply=_help_text())

    if lower == "/version":
        version_file = base_dir / "version.txt"
        try:
            version = version_file.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            version = "unknown"
        return SlashResult(handled=True, reply=f"Ann version: {version}")

    if lower == "/model":
        return SlashResult(handled=True, reply=f"Current LLM model: {controller.llm_model}")

    if lower == "/models":
        models = controller.ollama_client.get_installed_models()
        if not models:
            return SlashResult(
                handled=True,
                reply="No models found, or Ollama is not running.\nStart Ollama with: ollama serve",
            )
        current = controller.llm_model
        lines = ["Installed Ollama models:"]
        for m in models:
            tag = "  ← current" if m == current else ""
            lines.append(f"  • {m}{tag}")
        lines.append('\nTo switch, type: /switch <model name>')
        return SlashResult(handled=True, reply="\n".join(lines))

    if lower.startswith("/soul reset"):
        controller.soul_manager.reset()
        return SlashResult(
            handled=True,
            reply="Ann's soul state has been reset to defaults (Mood: Neutral, Energy: 100)."
        )

    if lower == "/soul":
        mood = controller.soul_manager.mood
        energy = controller.soul_manager.energy
        return SlashResult(
            handled=True,
            reply=(
                f"👻 Ann's Soul State\n"
                f"  • Mood (心境): {mood}\n"
                f"  • Energy (能量): {energy}/100\n"
                f"  • Info: Adjusts conversational tone dynamically while keeping response quality and accuracy at 100%."
            )
        )

    if lower.startswith("/switch"):
        parts = text.split(maxsplit=1)
        model_name = parts[1].strip() if len(parts) > 1 else ""
        from model_handler import _switch_model
        config_path = base_dir / "config.yml"
        reply = _switch_model(controller, config_path, model_name)
        return SlashResult(handled=True, reply=reply)

    if lower == "/moral" or lower.startswith("/moral "):
        return SlashResult(handled=True, reply=_handle_moral_command(text, base_dir))

    return SlashResult(handled=False)


def _handle_moral_command(text: str, base_dir: Path) -> str:
    """Handle '/moral stats' and '/moral flag [note]' (spec §11.5 governance)."""
    from moral_metrics import (
        format_report,
        latest_request_id,
        load_audit_records,
        load_corrections,
        record_correction,
        summarize,
    )

    logs_dir = base_dir / "logs"
    parts = text.split(maxsplit=2)
    sub = parts[1].lower() if len(parts) > 1 else "stats"
    records = load_audit_records(logs_dir)

    if sub == "stats":
        return format_report(summarize(records, load_corrections(logs_dir)))

    if sub == "flag":
        rid = latest_request_id(records)
        if not rid:
            return "No audited decision to flag yet. (Enable moral.logging in config.yml.)"
        note = parts[2].strip() if len(parts) > 2 else ""
        record_correction(logs_dir, rid, note)
        return (
            f"Flagged decision {rid} as a false positive. "
            "Thanks — this feeds the §11.5 over-refusal/over-escalation monitoring."
        )

    return "Usage: /moral stats | /moral flag [note]"


def _help_text() -> str:
    return (
        "Available slash commands:\n"
        "\n"
        "System\n"
        "  /version              Show current Ann version\n"
        "  /update               Check for updates (prompts for confirmation)\n"
        "  /y                    Confirm a pending /update\n"
        "\n"
        "LLM Model\n"
        "  /model                Show the current LLM model\n"
        "  /models               List all installed Ollama models\n"
        "  /switch <name>        Switch to a different LLM model\n"
        "\n"
        "Memory\n"
        "  /memory list          List all remembered facts\n"
        "  /memory add <text>    Manually add a memory\n"
        "  /memory edit <id> <text>  Edit a memory by ID\n"
        "  /memory delete <id>   Delete a memory by ID\n"
        "  /memory stats         Show memory usage statistics\n"
        "  /memory ui            Open memory management panel (GUI only)\n"
        "  /memory on            Enable memory\n"
        "  /memory off           Disable memory\n"
        "\n"
        "Soul (靈魂模組)\n"
        "  /soul                 Show Ann's current mood and energy\n"
        "  /soul reset           Reset Ann's soul state to defaults\n"
        "\n"
        "Moral Governance (道德治理)\n"
        "  /moral stats          Show moral decision metrics (spec §11.5)\n"
        "  /moral flag [note]    Flag the latest decision as a false positive\n"
    )
