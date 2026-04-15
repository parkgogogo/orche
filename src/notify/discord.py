from __future__ import annotations

from .base import Notifier
from .config import NotifyConfig
from .exceptions import NotifyConfigError, NotifyDeliveryError
from .http import HTTPClient, UrllibHTTPClient
from .models import DeliveryResult, NotifyEvent, ResolvedRoute

DEFAULT_USER_AGENT = "tmux-orche/0.1.1 (+https://github.com/parkgogogo/tmux-orche)"


class DiscordNotifier(Notifier):
    name = "discord"

    def __init__(
        self,
        config: NotifyConfig,
        *,
        http_client: HTTPClient | None = None,
    ) -> None:
        self.config = config
        self.http_client = http_client or UrllibHTTPClient()

    def send(self, event: NotifyEvent, route: ResolvedRoute) -> DeliveryResult:
        request_body = {
            "content": self._render_content(event),
            "allowed_mentions": self._allowed_mentions(),
        }
        base_headers = {
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        }
        discord = self.config.discord
        if discord.webhook_url:
            response = self.http_client.post(
                discord.webhook_url,
                headers=base_headers,
                json_body=request_body,
                timeout=discord.timeout_seconds,
            )
        else:
            if not discord.bot_token:
                raise NotifyConfigError(
                    "discord bot token is required when webhook_url is not configured"
                )
            if not route.target:
                raise NotifyConfigError(
                    "discord channel_id is required for bot-token delivery"
                )
            response = self.http_client.post(
                f"https://discord.com/api/v10/channels/{route.target}/messages",
                headers={
                    **base_headers,
                    "Authorization": f"Bot {discord.bot_token}",
                },
                json_body=request_body,
                timeout=discord.timeout_seconds,
            )
        if response.status_code >= 400:
            raise NotifyDeliveryError(
                f"discord delivery failed with status={response.status_code}: {response.body.strip()}"
            )
        return DeliveryResult(
            provider=self.name,
            ok=True,
            detail=str(response.status_code),
            target=route.target,
        )

    def _allowed_mentions(self) -> dict:
        if self.config.discord.mention_user_id:
            return {"parse": [], "users": [self.config.discord.mention_user_id]}
        return {"parse": []}

    def _render_content(self, event: NotifyEvent) -> str:
        content = event.summary or self.config.default_message_prefix
        normalized_status = event.status.strip().lower() or "success"
        if normalized_status != "success":
            content = f"[{normalized_status}] {content}"
        mention_user_id = self.config.discord.mention_user_id.strip()
        if mention_user_id:
            content = f"<@{mention_user_id}> {content}"
        if self.config.include_cwd and event.cwd:
            content += f"\ncwd: `{event.cwd}`"
        if self.config.include_session and event.session:
            content += f"\nsession: `{event.session}`"
        tail_text = str(event.metadata.get("tail_text") or "").strip()
        if tail_text:
            content += f"\n\nRecent output:\n{tail_text}"
        return content[: self.config.max_message_chars]
