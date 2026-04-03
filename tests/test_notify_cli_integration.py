from __future__ import annotations

from typer.testing import CliRunner

from cli import app
from notify.http import HTTPResponse

from .conftest import FakeHTTPClient, write_runtime_config


class StubHTTPClientFactory:
    def __init__(self, client):
        self.client = client

    def __call__(self):
        return self.client


def test_notify_hidden_command_reads_stdin_and_sends_message(xdg_runtime, monkeypatch):
    fake_client = FakeHTTPClient()
    monkeypatch.setattr("notify.discord.UrllibHTTPClient", StubHTTPClientFactory(fake_client))
    write_runtime_config(
        xdg_runtime["config_path"],
        {
            "notify_enabled": True,
            "discord_bot_token": "bot-token",
            "discord_channel_id": "1234567890",
            "session": "repo-codex-main",
            "cwd": "/tmp/repo",
        },
    )

    result = CliRunner().invoke(
        app,
        ["_notify"],
        input='{"event":"turn-complete","summary":"Done"}',
    )

    assert result.exit_code == 0
    assert "notify ok: provider=discord detail=200" in result.output
    assert fake_client.requests[0]["url"].endswith("/channels/1234567890/messages")
    assert fake_client.requests[0]["json_body"]["content"].startswith("<@1475734550813605959> Done")


def test_notify_hidden_command_verbose_prints_config_and_event(xdg_runtime, monkeypatch):
    fake_client = FakeHTTPClient()
    monkeypatch.setattr("notify.discord.UrllibHTTPClient", StubHTTPClientFactory(fake_client))
    write_runtime_config(
        xdg_runtime["config_path"],
        {
            "notify_enabled": True,
            "discord_bot_token": "bot-token",
            "discord_channel_id": "1234567890",
            "session": "repo-codex-main",
            "cwd": "/tmp/repo",
        },
    )

    result = CliRunner().invoke(
        app,
        ["_notify", "--verbose"],
        input='{"event":"turn-complete","summary":"Done"}',
    )

    assert result.exit_code == 0
    assert "notify config:" in result.output
    assert "discord.bot_token: set" in result.output
    assert "runtime.channel_id: 1234567890" in result.output
    assert "notify event:" in result.output
    assert "summary:" in result.output
    assert "Done" in result.output
    assert "discord: 1234567890" in result.output
    assert "notify ok: provider=discord detail=200" in result.output


def test_notify_hidden_command_failure_prints_error_and_returns_nonzero(xdg_runtime, monkeypatch):
    fake_client = FakeHTTPClient(responses=[HTTPResponse(403, '{"message":"forbidden"}')])
    monkeypatch.setattr("notify.discord.UrllibHTTPClient", StubHTTPClientFactory(fake_client))
    write_runtime_config(
        xdg_runtime["config_path"],
        {
            "notify_enabled": True,
            "discord_bot_token": "bot-token",
            "discord_channel_id": "1234567890",
            "session": "repo-codex-main",
            "cwd": "/tmp/repo",
        },
    )

    result = CliRunner().invoke(
        app,
        ["_notify"],
        input='{"event":"turn-complete","summary":"Done"}',
    )

    assert result.exit_code == 1
    assert "notify failed: provider=discord detail=discord delivery failed with status=403" in result.output


def test_notify_hidden_command_prefers_session_meta_channel_over_global_config(xdg_runtime, monkeypatch):
    fake_client = FakeHTTPClient()
    monkeypatch.setattr("notify.discord.UrllibHTTPClient", StubHTTPClientFactory(fake_client))
    write_runtime_config(
        xdg_runtime["config_path"],
        {
            "notify_enabled": True,
            "discord_bot_token": "bot-token",
            "discord_channel_id": "2222222222",
            "discord_session": "agent:main:discord:channel:2222222222",
            "session": "other-session",
            "cwd": "/tmp/other",
        },
    )

    from backend import save_meta

    save_meta(
        "repo-codex-main",
        {
            "session": "repo-codex-main",
            "cwd": "/tmp/repo",
            "agent": "codex",
            "pane_id": "%1",
            "notify_binding": {
                "provider": "discord",
                "target": "1111111111",
                "session": "agent:main:discord:channel:1111111111",
            },
        },
    )

    result = CliRunner().invoke(
        app,
        ["_notify", "--session", "repo-codex-main"],
        input='{"event":"turn-complete","summary":"Done"}',
    )

    assert result.exit_code == 0
    assert fake_client.requests[0]["url"].endswith("/channels/1111111111/messages")


def test_notify_hidden_command_uses_session_notify_binding_for_tmux_bridge(xdg_runtime, monkeypatch):
    captured = []
    write_runtime_config(
        xdg_runtime["config_path"],
        {
            "notify_enabled": True,
            "session": "other-session",
            "cwd": "/tmp/other",
        },
    )

    from backend import save_meta

    save_meta(
        "repo-codex-main",
        {
            "session": "repo-codex-main",
            "cwd": "/tmp/repo",
            "agent": "codex",
            "pane_id": "%1",
            "notify_binding": {
                "provider": "tmux-bridge",
                "target": "target-session",
            },
        },
    )

    monkeypatch.setattr(
        "notify.tmux_bridge.deliver_notify_to_session",
        lambda session, prompt: captured.append((session, prompt)) or "%2",
    )

    result = CliRunner().invoke(
        app,
        ["_notify", "--session", "repo-codex-main"],
        input='{"event":"turn-complete","summary":"Done"}',
    )

    assert result.exit_code == 0
    assert "notify ok: provider=tmux-bridge detail=delivered" in result.output
    assert captured[0][0] == "target-session"
