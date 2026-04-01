---
name: orche
description: Use orche CLI for tmux-backed Codex orchestration, especially for fire-and-forget workflows where you send work to Codex and return immediately. Use when managing persistent Codex sessions, sending tasks, checking status, or routing completion notifications to Discord.
---

# orche

Control plane for long-running Codex work in tmux sessions.

## Quick Start

```bash
# Create session
orche session-new --cwd /repo --agent codex --name my-session --discord-channel-id 123

# Send work (fire-and-forget)
orche send --session my-session "analyze this codebase"

# Check later
orche status --session my-session
orche read --session my-session --lines 50
```

## Core Commands

| Command | Purpose |
|---------|---------|
| `session-new` | Create/reuse a Codex tmux session |
| `send` | Send task and return immediately |
| `status` | Check session state |
| `read` | View terminal output |
| `history` | List control actions |
| `close` | Terminate session |

## Fire-and-Forget Workflow

1. `session-new` with `--discord-channel-id` for notify routing
2. `send` the task
3. Leave immediately (no polling)
4. Return when notify arrives or human asks
5. `read` before steering with `type` or `keys`

## Config

```bash
orche config set discord.bot-token "$TOKEN"
orche config set discord.channel-id "123"
orche config set discord.mention-user-id "123"
```

Config stored at `~/.config/orche/config.json`.
