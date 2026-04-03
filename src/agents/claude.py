from __future__ import annotations

import json
import shlex
from pathlib import Path

from .base import AgentPlugin, AgentRuntime
from .common import (
    DEFAULT_RUNTIME_HOME_ROOT,
    ensure_orche_shim,
    normalize_runtime_home,
    remove_runtime_home,
    session_key,
    validate_discord_channel_id,
    write_notify_hook,
    write_text_atomically,
)


READY_SURFACE_HINTS = (
    "Claude Code",
    "permission mode",
    "/help",
    "shift+tab",
    "esc to interrupt",
)
BLOCKING_PROMPT_HINTS = (
    "approval required",
    "approve this",
    "approve?",
    "allow this",
    "permission required",
    "waiting for approval",
    "waiting for user input",
    "press y to approve",
    "yes, don't ask again",
)


def default_claude_home_path(session: str) -> Path:
    return DEFAULT_RUNTIME_HOME_ROOT / f"orche-claude-{session_key(session)}"


def default_notify_hook_path(runtime_home: Path) -> Path:
    return runtime_home / "hooks" / "discord-turn-notify.sh"


def default_settings_path(runtime_home: Path) -> Path:
    return runtime_home / "settings.json"


def render_stop_hook_command(hook_path: Path, *, session: str, discord_channel_id: str | None) -> str:
    parts = ["/bin/bash", str(hook_path), "--session", session]
    if discord_channel_id:
        parts.extend(["--channel-id", validate_discord_channel_id(discord_channel_id)])
    return " ".join(shlex.quote(part) for part in parts)


def build_settings_payload(runtime_home: Path, *, session: str, discord_channel_id: str | None) -> dict[str, object]:
    return {
        "hooks": {
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": render_stop_hook_command(
                                default_notify_hook_path(runtime_home),
                                session=session,
                                discord_channel_id=discord_channel_id,
                            ),
                        }
                    ]
                }
            ]
        }
    }


def is_blocking_prompt_surface(capture: str) -> bool:
    lowered = capture.lower()
    return any(hint in lowered for hint in BLOCKING_PROMPT_HINTS)


class ClaudeAgent(AgentPlugin):
    name = "claude"
    display_name = "Claude Code"
    runtime_label = "Claude settings"
    login_prompts = ("Please run /login", "Login required")

    def ensure_managed_runtime(
        self,
        session: str,
        *,
        cwd: Path,
        discord_channel_id: str | None,
    ) -> AgentRuntime:
        _ = cwd
        target = default_claude_home_path(session)
        target.mkdir(parents=True, exist_ok=True)
        write_notify_hook(default_notify_hook_path(target))
        settings_payload = build_settings_payload(
            target,
            session=session,
            discord_channel_id=discord_channel_id,
        )
        write_text_atomically(
            default_settings_path(target),
            json.dumps(settings_payload, indent=2, ensure_ascii=False) + "\n",
        )
        return AgentRuntime(home=str(target.resolve()), managed=True, label=self.runtime_label)

    def build_launch_command(
        self,
        *,
        cwd: Path,
        runtime: AgentRuntime,
        session: str,
        discord_channel_id: str | None,
        approve_all: bool,
    ) -> str:
        _ = approve_all
        prefix = [f"cd {shlex.quote(str(cwd))}"]
        orche_shim = ensure_orche_shim()
        prefix.append(f"export ORCHE_BIN={shlex.quote(str(orche_shim))}")
        prefix.append(f"export PATH={shlex.quote(str(orche_shim.parent))}:$PATH")
        if session:
            prefix.append(f"export ORCHE_SESSION={shlex.quote(session)}")
        if discord_channel_id:
            prefix.append(f"export ORCHE_DISCORD_CHANNEL_ID={shlex.quote(validate_discord_channel_id(discord_channel_id))}")
        settings_path = default_settings_path(Path(normalize_runtime_home(runtime.home)))
        command = ["claude", "--dangerously-skip-permissions", "--settings", str(settings_path)]
        prefix.append(f"exec {' '.join(shlex.quote(part) for part in command)}")
        return " && ".join(prefix)

    def matches_process(self, pane_command: str, descendant_commands: list[str]) -> bool:
        if pane_command in {"claude", "node"}:
            return True
        for proc in descendant_commands:
            lowered = proc.lower()
            if re_matches_claude(lowered):
                return True
        return False

    def capture_has_ready_surface(self, capture: str, cwd: Path) -> bool:
        lowered = capture.lower()
        if is_blocking_prompt_surface(capture):
            return False
        has_brand = "claude code" in lowered or "\nclaude" in lowered or " claude" in lowered
        has_context = str(cwd) in capture or any(hint in lowered for hint in READY_SURFACE_HINTS) or bool(capture.strip())
        return has_brand and has_context

    def cleanup_runtime(self, runtime: AgentRuntime) -> None:
        if runtime.home:
            remove_runtime_home(runtime.home)


def re_matches_claude(command: str) -> bool:
    return "claude" in command or "claude-code" in command


PLUGINS = [ClaudeAgent()]
