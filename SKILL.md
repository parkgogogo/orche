---
name: orche
description: Use `orche` when OpenClaw or another agent needs to delegate work to a supported CLI agent in a persistent tmux session and return immediately. Use it for managed `session-new` handoff, native `orche codex` or `orche cc` passthrough sessions, single-channel notify bindings, reusing sessions, checking status, reading output, reviewing session history, closing finished sessions, or managing shared runtime config.
---

# orche

Use `orche` as the handoff boundary between OpenClaw and a long-running tmux-backed agent session.

## OpenClaw Workflow

1. Create or reuse a persistent managed session with `orche session-new`.
2. Send the task with `orche send`.
3. Return immediately. Do not wait for the agent in the same turn.
4. When notify arrives, inspect the same session with `status`, `read`, or `history`.
5. Close the session when the work is done.

## Quick Start

```bash
# Create or reuse a managed Codex session with a single notify binding
orche session-new --cwd /repo --agent codex --name repo-codex-main --notify-to tmux-bridge --notify-target repo-codex-reviewer

# Send work and return immediately
orche send --session repo-codex-main "analyze this codebase"

# Check later when notify arrives
orche status --session repo-codex-main
orche read --session repo-codex-main --lines 80
orche history --session repo-codex-main --limit 20

# Start a native passthrough tmux session for Codex
orche codex --cwd /repo --model gpt-5.4

# Start a native passthrough tmux session for Claude Code
orche cc --cwd /repo --print --help
```

## Commands

- `session-new`: create or reuse a persistent managed tmux session with orche metadata, optional managed runtime home, and an optional single notify binding
- `codex`, `claude`, `cc`: native passthrough shortcuts that wrap the upstream CLI in tmux and preserve the agent's native arguments and interaction style
- `send`: send a task into an existing managed session and return immediately
- `status`: show whether the session and agent process are still running
- `read`: inspect recent terminal output from the live session
- `history`: inspect recent local control actions for that session
- `close`: terminate the session when it is no longer needed
- `config`: read and update shared runtime configuration

Use the shortcut commands when you want behavior close to running the upstream CLI directly. Use `session-new` when you need orche-managed features such as notify binding or managed runtime homes.

## Notify

Set exactly one notify channel at session creation time with `session-new`:

```bash
orche session-new \
  --cwd /repo \
  --agent claude \
  --name repo-claude-review \
  --notify-to discord \
  --notify-target 123456789012345678
```

`--notify-to` selects the provider. `--notify-target` carries the provider-specific target value.

Current built-in providers include:

- `discord`: use a Discord channel id as `--notify-target`
- `tmux-bridge`: use a target tmux session name as `--notify-target`

Notify is single-channel per session. To change the notify target or provider, close the session and create a new one.

The native shortcut commands `orche codex`, `orche claude`, and `orche cc` do not use orche notify bindings or managed settings. They only add tmux session naming and tmux-backed execution around the native CLI.

## Config

Use `orche config` to manage shared runtime settings:

```bash
orche config list
orche config set discord.bot-token "$TOKEN"
orche config set discord.mention-user-id "123"
orche config set notify.enabled true
```

Config path:

```text
~/.config/orche/config.json
```

## Agent Plugins

Agents are loaded through a plugin registry. The current built-in plugins are `codex` and `claude`.

- Add or update an agent plugin module under `src/agents/`
- Expose a `PLUGINS` list from that module
- Register the module in `src/agents/registry.py`
- The agent then becomes available to `orche session-new --agent ...`
- Add a native shortcut command in `src/cli.py` if you also want `orche <agent>` style passthrough

This keeps agent-specific launch, ready detection, interrupt, and runtime behavior isolated from the generic tmux/session orchestration layer.

## Troubleshooting

### Cancel a stuck turn

If a managed agent session is stuck, running in the wrong direction, or needs to be stopped without losing the session:

```bash
orche cancel --session repo-codex-main
```

This interrupts the current agent turn but keeps the session alive, allowing you to read output and send a corrected task.

Compare with close:

- `cancel`: interrupt current turn, keep session
- `close`: end entire session
