"""
system_commands.py — Registry for keyword-triggered system commands.

Each SystemCommandDef describes one system action (exit, restart, …).
Both CLI and GUI iterate this registry instead of maintaining separate
hardcoded keyword sets.

To add a new system command, append one SystemCommandDef to SYSTEM_COMMANDS.
No other file needs to change.

Exit codes (must match launcher.py expectations):
  0  — clean exit
  3  — restart (EXIT_RESTART)
  42 — update  (EXIT_UPDATE)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SystemCommandDef:
    keywords: frozenset[str]   # matched against lowercased user input
    exit_code: int             # process exit code the caller should use
    reply: str                 # message shown to the user before exiting
    gui_title: str             # title bar label shown in GUI during the delay


# ---------------------------------------------------------------------------
# Registry — add new entries here only
# ---------------------------------------------------------------------------

SYSTEM_COMMANDS: list[SystemCommandDef] = [
    SystemCommandDef(
        keywords=frozenset({
            "exit", "close", "terminate", "close the window", "shut down",
            "再見", "關閉程式", "關閉",
        }),
        exit_code=0,
        reply="再見！有需要隨時找我。",
        gui_title="Goodbye...",
    ),
    SystemCommandDef(
        keywords=frozenset({
            "restart", "reboot", "重啟", "重新啟動",
        }),
        exit_code=3,  # EXIT_RESTART
        reply="好的，我現在重新啟動，稍後見！",
        gui_title="Restarting...",
    ),
]


def match_system_command(user_input_lower: str) -> SystemCommandDef | None:
    """Return the first SystemCommandDef whose keywords contain user_input_lower, or None."""
    for cmd in SYSTEM_COMMANDS:
        if user_input_lower in cmd.keywords:
            return cmd
    return None
