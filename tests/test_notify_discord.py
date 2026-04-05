from __future__ import annotations

import pytest

from notify.config import DiscordNotifyConfig, NotifyConfig
from notify.discord import DEFAULT_USER_AGENT, DiscordNotifier
from notify.exceptions import NotifyConfigError, NotifyDeliveryError
from notify.http import HTTPResponse
from notify.models import NotifyEvent, ResolvedRoute


def test_discord_notifier_sends_via_bot_token(fake_http_client):
    notifier = DiscordNotifier(
        NotifyConfig(discord=DiscordNotifyConfig(bot_token="bot-token", mention_user_id="42")),
        http_client=fake_http_client,
    )

    result = notifier.send(
        NotifyEvent(event="turn-complete", summary="done", session="demo", status="success"),
        ResolvedRoute(provider="discord", target="123"),
    )

    assert result.ok is True
    assert fake_http_client.requests[0]["headers"]["Authorization"] == "Bot bot-token"
    assert fake_http_client.requests[0]["headers"]["User-Agent"] == DEFAULT_USER_AGENT
    assert fake_http_client.requests[0]["json_body"]["allowed_mentions"]["users"] == ["42"]


def test_discord_notifier_sends_via_webhook(fake_http_client):
    notifier = DiscordNotifier(
        NotifyConfig(discord=DiscordNotifyConfig(webhook_url="https://discord.test/webhook")),
        http_client=fake_http_client,
    )

    notifier.send(
        NotifyEvent(event="turn-complete", summary="done", session="demo", status="success"),
        ResolvedRoute(provider="discord", target="123"),
    )

    assert fake_http_client.requests[0]["url"] == "https://discord.test/webhook"
    assert "Authorization" not in fake_http_client.requests[0]["headers"]
    assert fake_http_client.requests[0]["headers"]["User-Agent"] == DEFAULT_USER_AGENT


def test_discord_notifier_requires_token_or_webhook(fake_http_client):
    notifier = DiscordNotifier(NotifyConfig(discord=DiscordNotifyConfig()), http_client=fake_http_client)

    with pytest.raises(NotifyConfigError):
        notifier.send(
            NotifyEvent(event="turn-complete", summary="done", session="demo", status="success"),
            ResolvedRoute(provider="discord", target="123"),
        )


def test_discord_notifier_requires_channel_for_bot_delivery(fake_http_client):
    notifier = DiscordNotifier(
        NotifyConfig(discord=DiscordNotifyConfig(bot_token="bot-token")),
        http_client=fake_http_client,
    )

    with pytest.raises(NotifyConfigError):
        notifier.send(
            NotifyEvent(event="turn-complete", summary="done", session="demo", status="success"),
            ResolvedRoute(provider="discord", target=""),
        )


def test_discord_notifier_raises_delivery_error(fake_http_client):
    fake_http_client.responses = [HTTPResponse(500, "boom")]
    notifier = DiscordNotifier(
        NotifyConfig(discord=DiscordNotifyConfig(bot_token="bot-token")),
        http_client=fake_http_client,
    )

    with pytest.raises(NotifyDeliveryError):
        notifier.send(
            NotifyEvent(event="turn-complete", summary="done", session="demo", status="success"),
            ResolvedRoute(provider="discord", target="123"),
        )


def test_discord_notifier_supports_empty_mentions(fake_http_client):
    notifier = DiscordNotifier(
        NotifyConfig(discord=DiscordNotifyConfig(bot_token="bot-token", mention_user_id="")),
        http_client=fake_http_client,
    )

    notifier.send(
        NotifyEvent(event="turn-complete", summary="done", session="demo", status="success"),
        ResolvedRoute(provider="discord", target="123"),
    )

    assert fake_http_client.requests[0]["json_body"]["allowed_mentions"] == {"parse": []}


def test_discord_notifier_renders_status_prefix_and_respects_disabled_session_line(fake_http_client):
    notifier = DiscordNotifier(
        NotifyConfig(
            include_session=False,
            discord=DiscordNotifyConfig(bot_token="bot-token", mention_user_id=""),
        ),
        http_client=fake_http_client,
    )

    notifier.send(
        NotifyEvent(
            event="turn-complete",
            summary="done",
            session="demo",
            cwd="/tmp/repo",
            status="failure",
        ),
        ResolvedRoute(provider="discord", target="123"),
    )

    assert fake_http_client.requests[0]["json_body"]["content"] == "[failure] done\ncwd: `/tmp/repo`"


def test_discord_notifier_appends_recent_output(fake_http_client):
    notifier = DiscordNotifier(
        NotifyConfig(
            include_session=False,
            discord=DiscordNotifyConfig(bot_token="bot-token", mention_user_id=""),
        ),
        http_client=fake_http_client,
    )

    notifier.send(
        NotifyEvent(
            event="startup-blocked",
            summary="Codex startup blocked",
            session="demo",
            cwd="/tmp/repo",
            status="startup-blocked",
            metadata={"tail_text": "line1\nline2"},
        ),
        ResolvedRoute(provider="discord", target="123"),
    )

    assert (
        fake_http_client.requests[0]["json_body"]["content"]
        == "[startup-blocked] Codex startup blocked\ncwd: `/tmp/repo`\n\nRecent output:\nline1\nline2"
    )
