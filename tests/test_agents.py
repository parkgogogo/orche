from __future__ import annotations

import json
from pathlib import Path

import backend


def test_supported_agents_include_codex_and_claude():
    assert backend.supported_agent_names() == ("claude", "codex")


def test_ensure_managed_claude_home_writes_stop_hook(tmp_path, monkeypatch):
    monkeypatch.setattr(backend.claude_agent_module, "DEFAULT_RUNTIME_HOME_ROOT", tmp_path / "managed")

    target = backend.ensure_managed_claude_home(
        "repo-claude-main",
        cwd=tmp_path,
        discord_channel_id="1234567890",
    )

    settings_path = Path(target) / "settings.json"
    hook_path = Path(target) / "hooks" / "discord-turn-notify.sh"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    command = payload["hooks"]["Stop"][0]["hooks"][0]["command"]

    assert hook_path.exists()
    assert "--session repo-claude-main" in command
    assert "--channel-id 1234567890" in command


def test_ensure_session_supports_claude_agent(xdg_runtime, tmp_path, monkeypatch):
    monkeypatch.setattr(backend.claude_agent_module, "DEFAULT_RUNTIME_HOME_ROOT", tmp_path / "managed")
    monkeypatch.setattr(backend, "ensure_pane", lambda session, cwd, agent: "%7")
    monkeypatch.setattr(backend, "ensure_agent_running", lambda *args, **kwargs: "%7")

    pane_id = backend.ensure_session("demo-claude", tmp_path, "claude", discord_channel_id="123")
    meta = backend.load_meta("demo-claude")

    assert pane_id == "%7"
    assert meta["agent"] == "claude"
    assert meta["runtime_home"].endswith("demo-claude")
    assert meta["runtime_label"] == "Claude settings"
