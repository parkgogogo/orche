# Developing Notify Plugins

`orche` routes completion and status events through notify plugins. A notify plugin knows how to take a normalized event payload and deliver it to a specific destination (Discord, tmux bridge, webhook, etc.).

## Plugin Interface

A notify plugin must implement:

1. **Name** — The provider identifier (`discord`, `tmux`, etc.)
2. **Route resolver** — Given a notify target string, return whether this plugin handles it
3. **Event dispatcher** — Accept a normalized payload and deliver it

## File Location

Notify plugins live in `src/notify/`. The `NotificationService` in `src/notify/service.py` coordinates routing.

## Example: Minimal Notify Plugin

```python
from .payload import NotificationPayload

class MyNotifier:
    name = "my_notifier"

    def resolve_routes(self, target: str) -> bool:
        return target.startswith("my:")

    def dispatch_event(self, payload: NotificationPayload):
        target = payload.target
        message = payload.build_message()
        # Deliver `message` to `target`
        print(f"[MY] {target}: {message}")
```

## Registration

Import your notifier in `src/notify/service.py` and add it to the `NotificationService` notifiers list:

```python
from .my_notifier import MyNotifier

notifiers = [
    DiscordNotifier(),
    TmuxBridgeNotifier(),
    MyNotifier(),
]
```

## Payload Structure

The `NotificationPayload` object provides:

- `session` — The originating session name
- `target` — The raw notify target string
- `event_type` — `completed`, `needs_input`, `error`, etc.
- `content` / `summary` — The message body
- `build_message()` — A formatted string suitable for delivery

Use these fields to construct the appropriate message for your destination.
