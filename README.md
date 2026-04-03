[中文](README.zh.md) · [Install Guide](https://github.com/parkgogogo/tmux-orche/raw/main/install.md)

# tmux-orche

Persistent tmux-backed agent sessions for delegation, review, and takeover.

`tmux-orche` is for the gap between "run an agent once" and "manually babysit tmux panes all day".

It lets you:

- open a named agent session once and keep reusing it
- hand work off and return immediately
- inspect progress later without losing terminal state
- route replies explicitly to another session or to Discord
- take over the live TTY at any point

If you already use Codex or Claude Code in tmux, `orche` gives that workflow stable names, explicit session state, and a clean handoff loop.

## Why Use It

Most agent workflows break down in the same places:

- the session disappears after one command
- you lose the exact terminal state that produced the result
- follow-up prompts start from scratch
- multi-agent review flows turn into ad-hoc tmux scripting
- notifications become implicit and hard to reason about

`orche` fixes that by making the session the primary unit of work.

You do not talk to "some pane". You talk to a named session with:

- a working directory
- an agent type
- a persistent tmux pane
- optional explicit notify routing
- later inspection and takeover

## What Makes It Different

### Session-first, not pane-first

You work with `repo-worker`, `repo-reviewer`, or `auth-fixer`, not `%17`.

### Handoff-first, not babysitting-first

The default flow is:

1. `open`
2. `prompt`
3. leave
4. `status` / `read` later

### Explicit notify, no default route

Notifications only fire when you explicitly bind a route.

- `tmux:<session>`
- `discord:<channel-id>`

There is no implicit global default delivery path.

### Works for both background delegation and live takeover

Use `read` and `status` for normal follow-up.
Use `attach` when you want to directly take control of the terminal.

## Core Workflow

```bash
# open a worker session once
orche open \
  --cwd /path/to/repo \
  --agent codex \
  --name repo-worker \
  --notify tmux:repo-reviewer

# send work
orche prompt repo-worker "analyze the failing tests and propose a fix"

# come back later
orche status repo-worker
orche read repo-worker --lines 120

# take over if needed
orche attach repo-worker

# close when finished
orche close repo-worker
```

That is the intended model: persistent session, explicit handoff, later inspection.

## Best Fit Scenarios

`tmux-orche` is a good fit when you want:

- one reviewer session coordinating multiple workers
- a long-running implementation or research worker
- stable session names across multiple prompts
- terminal-native agents that sometimes ask for input
- explicit tmux-based notify between sessions
- a way to jump into the exact live terminal when automation is not enough

It is less useful when you only need one short-lived command and do not plan to come back to the session.

## Quick Start

Open a managed session with explicit notify:

```bash
orche open \
  --cwd /path/to/repo \
  --agent codex \
  --name repo-worker \
  --notify tmux:repo-reviewer
```

Send work:

```bash
orche prompt repo-worker "implement the parser refactor"
```

Inspect later:

```bash
orche status repo-worker
orche read repo-worker --lines 120
orche list
```

Answer interactive prompts:

```bash
orche input repo-worker "yes"
orche key repo-worker Enter
```

Take over the TTY:

```bash
orche attach repo-worker
```

## Managed vs Native Sessions

### Managed session

Use managed mode for normal delegation:

```bash
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer
```

This is the default recommendation.

### Native session

Use native mode when you need raw agent CLI args:

```bash
orche open --cwd /repo --agent claude -- --print --help
```

Rules:

- raw agent args must come after `--`
- native sessions do not use `--notify`
- do not mix raw agent args with managed notify routing

## Command Model

- `orche open`
  Create or reuse a named session.
- `orche prompt`
  Send a prompt into an existing session.
- `orche status`
  Check whether the pane and agent are alive, and whether a turn is pending.
- `orche read`
  Read recent terminal output.
- `orche attach`
  Attach your terminal to the live tmux session.
- `orche input`
  Type text without pressing Enter.
- `orche key`
  Send special keys such as `Enter`, `Escape`, or `C-c`.
- `orche list`
  List locally known sessions.
- `orche cancel`
  Interrupt the current turn but keep the session alive.
- `orche close`
  End the session and clean up state.
- `orche whoami`
  Print the current session id.
- `orche config`
  Read or update shared runtime config.

## Multi-Agent Review Pattern

```bash
# reviewer
orche open --cwd /repo --agent codex --name repo-reviewer --notify discord:123456789012345678

# worker reports back to reviewer
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer

# send implementation work
orche prompt repo-worker "implement the parser refactor"

# later inspect reviewer
orche read repo-reviewer --lines 120
```

This gives you a durable reviewer/worker loop without ad-hoc tmux scripting.

## Notify

Notify is explicit.

`orche open --notify` accepts:

- `tmux:<target-session>`
- `discord:<channel-id>`

Examples:

```bash
orche open --cwd /repo --agent codex --name repo-reviewer --notify discord:123456789012345678
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer
```

Notes:

- use `tmux:<session>` for agent-to-agent routing
- use `discord:<channel-id>` only when you want Discord delivery
- changing notify target means opening a new session

## Installation

Full install guide: <https://github.com/parkgogogo/tmux-orche/raw/main/install.md>

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

## Config

```bash
orche config list
orche config set discord.bot-token "$BOT_TOKEN"
orche config set discord.mention-user-id 123456789012345678
orche config set notify.enabled true
```

Config file:

```text
~/.config/orche/config.json
```

State directory:

```text
~/.local/share/orche/
```

## Prerequisites

- `tmux`
- `codex` CLI and/or `claude` CLI
- Python `3.9+`

## License

[MIT](LICENSE)
