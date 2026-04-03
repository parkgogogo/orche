from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from typing import Any, Callable, Mapping, Sequence

from .config import load_notify_config
from .http import HTTPClient
from .models import DeliveryResult, NotifyEvent, ResolvedRoute
from .payload import build_message_from_payload
from .registry import DEFAULT_REGISTRY, NotifierRegistry


class NotificationService:
    def __init__(
        self,
        *,
        registry: NotifierRegistry | None = None,
        http_client: HTTPClient | None = None,
    ) -> None:
        self.registry = registry or DEFAULT_REGISTRY
        self.http_client = http_client

    def send(
        self,
        event: NotifyEvent,
        routes: Sequence[ResolvedRoute],
        config,
    ) -> Sequence[DeliveryResult]:
        if not routes:
            return ()
        notifiers = {
            notifier.name: notifier
            for notifier in self.registry.create_many(config, http_client=self.http_client)
        }
        results: list[DeliveryResult] = []
        with ThreadPoolExecutor(max_workers=max(1, len(routes))) as executor:
            future_map = {}
            for route in routes:
                notifier = notifiers.get(route.provider)
                if notifier is None:
                    supported = ", ".join(sorted(notifiers))
                    results.append(
                        DeliveryResult(
                            provider=route.provider,
                            ok=False,
                            detail=f"Unsupported notifier: {route.provider}. Supported notifiers: {supported}",
                            target=route.target,
                        )
                    )
                    continue
                future = executor.submit(notifier.send, event, route)
                future_map[future] = route
            for future in as_completed(future_map):
                route = future_map[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    results.append(
                        DeliveryResult(
                            provider=route.provider,
                            ok=False,
                            detail=str(exc),
                            target=route.target,
                        )
                    )
        return tuple(sorted(results, key=lambda result: (result.provider, result.target)))


def resolve_routes(
    *,
    event: NotifyEvent,
    runtime_config: Mapping[str, Any],
    notify_config,
    explicit_channel_id: str = "",
) -> Sequence[ResolvedRoute]:
    routes: list[ResolvedRoute] = []
    configured_routes = runtime_config.get("notify_routes")
    provider_routes = configured_routes if isinstance(configured_routes, Mapping) else {}
    discord_route = provider_routes.get("discord") if isinstance(provider_routes.get("discord"), Mapping) else {}
    normalized_channel_id = re.sub(
        r"\s+",
        "",
        str(
            explicit_channel_id
            or discord_route.get("channel_id")
            or runtime_config.get("discord_channel_id")
            or runtime_config.get("codex_turn_complete_channel_id")
            or ""
        ),
    )
    for provider in notify_config.providers:
        if provider == "discord" and normalized_channel_id:
            routes.append(
                ResolvedRoute(
                    provider=provider,
                    target=normalized_channel_id,
                    session=event.session,
                )
            )
        elif provider != "discord":
            provider_route = provider_routes.get(provider)
            route_payload = provider_route if isinstance(provider_route, Mapping) else {}
            target = str(
                route_payload.get("target")
                or route_payload.get("target_session")
                or route_payload.get("session")
                or ""
            ).strip()
            routes.append(
                ResolvedRoute(
                    provider=provider,
                    target=target,
                    session=event.session,
                    metadata=dict(route_payload),
                )
            )
    return tuple(routes)


def dispatch_payload(
    payload_text: str,
    *,
    runtime_config: Mapping[str, Any],
    summary_loader: Callable[[str], str],
    explicit_channel_id: str = "",
    explicit_session: str = "",
    status: str = "success",
    env: Mapping[str, str] | None = None,
    service: NotificationService | None = None,
) -> Sequence[DeliveryResult]:
    notify_config = load_notify_config(runtime_config, env=env)
    if not notify_config.enabled:
        return ()
    event = build_message_from_payload(
        payload_text,
        notify_config=notify_config,
        runtime_config=runtime_config,
        summary_loader=summary_loader,
        explicit_session=explicit_session,
        status=status,
    )
    if event is None:
        return ()
    routes = resolve_routes(
        event=event,
        runtime_config=runtime_config,
        notify_config=notify_config,
        explicit_channel_id=explicit_channel_id,
    )
    if not routes:
        return ()
    notifier_service = service or NotificationService()
    return notifier_service.send(event, routes, notify_config)
