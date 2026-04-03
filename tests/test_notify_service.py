from __future__ import annotations

import pytest

from notify.base import Notifier
from notify.config import NotifyConfig
from notify.models import DeliveryResult, NotifyEvent, ResolvedRoute
from notify.registry import NotifierRegistry
from notify.service import NotificationService, dispatch_payload, resolve_routes


class SuccessNotifier(Notifier):
    name = "alpha"

    def send(self, event, route):
        return DeliveryResult(provider=self.name, ok=True, detail=event.summary, target=route.target)


class FailingNotifier(Notifier):
    name = "beta"

    def send(self, event, route):
        raise RuntimeError("boom")


class CapturingService:
    def __init__(self):
        self.calls = []

    def send(self, event, routes, config):
        self.calls.append((event, routes, config))
        return (DeliveryResult(provider="discord", ok=True, detail=event.summary),)


class BaseNotifier(Notifier):
    name = "base"

    def send(self, event, route):
        return super().send(event, route)


def test_notification_service_returns_success_and_failure_results():
    registry = NotifierRegistry()
    registry.register("alpha", lambda config, http_client: SuccessNotifier())
    registry.register("beta", lambda config, http_client: FailingNotifier())
    service = NotificationService(registry=registry)

    results = service.send(
        NotifyEvent(event="turn-complete", summary="done", session="demo", status="success"),
        (
            ResolvedRoute(provider="alpha", target="one"),
            ResolvedRoute(provider="beta", target="two"),
        ),
        NotifyConfig(providers=("alpha", "beta")),
    )

    assert list(results) == [
        DeliveryResult(provider="alpha", ok=True, detail="done", target="one"),
        DeliveryResult(provider="beta", ok=False, detail="boom", target="two"),
    ]


def test_dispatch_payload_returns_empty_when_disabled():
    results = dispatch_payload(
        '{"event":"turn-complete","summary":"done"}',
        runtime_config={"notify_enabled": False, "discord_channel_id": "123"},
        summary_loader=lambda session: "",
    )

    assert results == ()


def test_dispatch_payload_builds_message_and_uses_service():
    service = CapturingService()

    results = dispatch_payload(
        '{"event":"turn-complete","summary":"done"}',
        runtime_config={"discord_channel_id": "123", "discord_bot_token": "token"},
        summary_loader=lambda session: "",
        explicit_session="demo",
        service=service,
    )

    assert results[0].ok is True
    event, routes, config = service.calls[0]
    assert event.session == "demo"
    assert routes[0].provider == "discord"
    assert config.providers == ("discord",)


def test_notification_service_returns_empty_when_no_notifiers():
    service = NotificationService(registry=NotifierRegistry())

    results = service.send(
        NotifyEvent(event="turn-complete", summary="done", session="demo", status="success"),
        (),
        NotifyConfig(providers=()),
    )

    assert results == ()


def test_notification_service_marks_route_without_notifier_as_failure():
    registry = NotifierRegistry()
    registry.register("alpha", lambda config, http_client: SuccessNotifier())
    service = NotificationService(registry=registry)

    results = service.send(
        NotifyEvent(event="turn-complete", summary="done", session="demo", status="success"),
        (ResolvedRoute(provider="beta", target="missing"),),
        NotifyConfig(providers=("alpha",)),
    )

    assert results == (
        DeliveryResult(
            provider="beta",
            ok=False,
            detail="Unsupported notifier: beta. Supported notifiers: alpha",
            target="missing",
        ),
    )


def test_dispatch_payload_returns_empty_for_invalid_payload():
    results = dispatch_payload(
        "not-json",
        runtime_config={"discord_channel_id": "123", "discord_bot_token": "token"},
        summary_loader=lambda session: "",
    )

    assert results == ()


def test_resolve_routes_uses_explicit_channel_for_discord():
    event = NotifyEvent(event="turn-complete", summary="done", session="demo", status="success")

    routes = resolve_routes(
        event=event,
        runtime_config={"discord_channel_id": "123"},
        notify_config=NotifyConfig(providers=("discord",)),
        explicit_channel_id="456",
    )

    assert routes == (ResolvedRoute(provider="discord", target="456", session="demo"),)


def test_resolve_routes_includes_non_discord_providers_without_target():
    event = NotifyEvent(event="turn-complete", summary="done", session="demo", status="success")

    routes = resolve_routes(
        event=event,
        runtime_config={"notify_routes": {"tmux-bridge": {"target_session": "target-session"}}},
        notify_config=NotifyConfig(providers=("tmux-bridge",)),
    )

    assert routes == (
        ResolvedRoute(
            provider="tmux-bridge",
            target="target-session",
            session="demo",
            metadata={"target_session": "target-session"},
        ),
    )


def test_resolve_routes_skips_discord_without_channel_target():
    event = NotifyEvent(event="turn-complete", summary="done", session="demo", status="success")

    routes = resolve_routes(
        event=event,
        runtime_config={},
        notify_config=NotifyConfig(providers=("discord", "tmux-bridge")),
    )

    assert routes == (ResolvedRoute(provider="tmux-bridge", session="demo"),)


def test_resolve_routes_prefers_notify_routes_discord_channel():
    event = NotifyEvent(event="turn-complete", summary="done", session="demo", status="success")

    routes = resolve_routes(
        event=event,
        runtime_config={"notify_routes": {"discord": {"channel_id": "789"}}},
        notify_config=NotifyConfig(providers=("discord",)),
    )

    assert routes == (ResolvedRoute(provider="discord", target="789", session="demo"),)


def test_dispatch_payload_returns_empty_when_event_has_no_routes():
    results = dispatch_payload(
        '{"event":"turn-complete","summary":"done"}',
        runtime_config={"notify_enabled": True},
        summary_loader=lambda session: "",
    )

    assert results == ()


def test_notifier_base_raises_not_implemented():
    notifier = BaseNotifier()

    with pytest.raises(NotImplementedError):
        notifier.send(
            NotifyEvent(event="turn-complete", summary="done", session="demo", status="success"),
            ResolvedRoute(provider="base"),
        )
