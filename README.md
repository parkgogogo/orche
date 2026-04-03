[中文](README.zh.md) · [Install Guide](https://github.com/parkgogogo/tmux-orche/raw/main/install.md)

# tmux-orche

tmux-backed CLI agent orchestration for OpenClaw fire-and-forget workflows.

`tmux-orche` lets OpenClaw hand work to a supported CLI agent such as Codex or Claude Code, return immediately, and continue later through the same persistent tmux session. That keeps OpenClaw from burning tokens while the agent works in the background.

## OpenClaw Workflow

1. OpenClaw creates or reuses an agent session with `orche session-new`.
2. OpenClaw sends the task with `orche send`.
3. `orche` returns immediately.
4. The agent keeps running in tmux.
5. When notify arrives, OpenClaw or another agent inspects the same session with `status`, `read`, or `history`.
6. The session stays available until it is explicitly closed.

## Quick Start

Create or reuse a session:

```bash
orche session-new \
  --cwd /path/to/repo \
  --agent codex \
  --name repo-codex-main \
  --notify-to tmux-bridge \
  --notify-target repo-codex-reviewer
```

Send work and return immediately:

```bash
orche send --session repo-codex-main "analyze the failing tests and propose a fix"
```

Inspect the same session later:

```bash
orche status --session repo-codex-main
orche read --session repo-codex-main --lines 120
orche history --session repo-codex-main --limit 20
```

Close it when done:

```bash
orche close --session repo-codex-main
```

## Installation

Full step-by-step install guide: <https://github.com/parkgogogo/tmux-orche/raw/main/install.md>

Install from PyPI:

```bash
pip install tmux-orche
```

Install with `uv`:

```bash
uv tool install tmux-orche
```

Install from source:

```bash
git clone https://github.com/parkgogogo/orche
cd orche
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install .
```

## Commands

- `orche session-new --cwd /repo --agent codex --name repo-codex-main --notify-to tmux-bridge --notify-target repo-codex-reviewer`
  Create or reuse a persistent Codex tmux session.
- `orche session-new --cwd /repo --agent claude --name repo-claude-main --notify-to discord --notify-target 123456789012345678`
  Create or reuse a persistent Claude Code tmux session.
- `orche codex --cwd /repo --model gpt-5.4`
  Run native Codex inside tmux with the default session name for that repo.
- `orche cc --session-name repo-claude-review --print --help`
  Run native Claude Code inside tmux with passthrough CLI args and an optional session name override.
- `orche send --session repo-codex-main "review the recent auth changes"`
  Send a task into an existing session and return immediately.
- `orche status --session repo-codex-main`
  Check whether the session and Codex process are still running.
- `orche read --session repo-codex-main --lines 80`
  Read recent terminal output from the live session.
- `orche type --session repo-codex-main --text "yes"`
  Type text into the live Codex session without pressing Enter.
- `orche keys --session repo-codex-main --key Enter`
  Send one or more key presses to the live Codex session.
- `orche history --session repo-codex-main --limit 20`
  Show recent local control actions for that session.
- `orche sessions list`
  Show stored sessions from local metadata.
- `orche sessions clearall`
  Close and remove all stored sessions.
- `orche close --session repo-codex-main`
  Close the session when the work is finished.
- `orche config list`
  Show current runtime configuration.

## Interactive Input

Use `type` and `keys` when Codex is waiting on an interactive prompt inside the tmux session.

Read the latest output first:

```bash
orche read --session repo-codex-main --lines 40
```

Type text without submitting it:

```bash
orche type --session repo-codex-main --text "yes"
```

Then send Enter:

```bash
orche keys --session repo-codex-main --key Enter
```

This is useful for prompts such as trust confirmations, shell confirmations, or any other step where Codex is paused waiting for input.

You can also send multiple keys in one command:

```bash
orche keys --session repo-codex-main --key Down --key Down --key Enter
```

## Config

Manage runtime settings:

```bash
orche config list
orche config set discord.bot-token "$BOT_TOKEN"
orche config set discord.mention-user-id 123456789012345678
orche config set notify.enabled true
```

Set notify targets when creating the session:

```bash
orche session-new \
  --cwd /repo \
  --agent codex \
  --name repo-codex-main \
  --notify-to discord \
  --notify-target 123456789012345678
```

Notify uses a single bound channel per session. To change it, close the session and create a new one with the desired `--notify-to` and `--notify-target`.

Config file:

```text
~/.config/orche/config.json
```

State directory:

```text
~/.local/share/orche/
```

## Troubleshooting

### Cancel a stuck turn

If Codex is stuck, running in the wrong direction, or needs to be stopped without losing the session:

```bash
orche cancel --session repo-codex-main
```

This interrupts the current Codex turn but keeps the session alive, allowing you to read output and send a corrected task.

Compare with close:

- `cancel`: Interrupt current turn, keep session (for stuck or still-running tasks)
- `close`: End entire session (for completed or abandoned tasks)

## Prerequisites

- `tmux`
- `tmux-bridge`
- `codex` CLI and/or `claude` CLI
- Python `3.9+`

## License

[MIT](LICENSE)
