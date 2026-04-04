---
name: orche
description: Use `orche` when you need to hand work off to a persistent tmux-backed agent session, continue your own turn, and come back later only when inspection or follow-up is needed. It covers opening or reusing sessions, sending prompts, reading live output, answering interactive prompts, attaching mid-flight, and routing explicit notify events to tmux or Discord.
---

# orche

`orche` is the session-oriented handoff boundary for long-running CLI agents.

Use it when you want:

- a persistent worker session instead of a one-shot subprocess
- explicit session names and reusable state
- agent-to-agent notify through tmux
- later inspection without blocking on the worker

Prefer `orche` over ad-hoc `tmux send-keys` when the target is an `orche`-managed agent session.

## Core Model

`orche` is organized around one resource: the session.

- `open` creates or reuses a named session
- `prompt` sends work into an existing session
- `status`, `read`, `list`, and `attach` inspect or enter the session
- `input` and `key` answer interactive prompts
- `cancel` interrupts the current turn but keeps the session alive
- `close` ends the session cleanly

The normal pattern is:

1. open or reuse a session
2. send work
3. return immediately
4. inspect later only if needed

## Default Workflow

Use this flow unless you have a strong reason not to:

```bash
# 1. open a managed worker with explicit notify routing
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer

# 2. send work
orche prompt repo-worker "implement the parser refactor"

# 3. leave the worker alone

# 4. inspect later if needed
orche status repo-worker
orche read repo-worker --lines 120
orche list
```

Treat `prompt` as fire-and-follow-up, not fire-and-busy-wait.

## Session Awareness First

Before opening a worker or deciding a notify route, first determine whether you are already inside an `orche` session.

Start with:

```bash
orche whoami
```

Interpretation:

- if it returns a session name, you are inside an `orche`-managed tmux pane and that session is your safest default tmux notify target
- if it fails, do not guess that you are inside a session; you are likely in a normal shell or outside the worker pane

If `whoami` fails but you still need context, inspect the known sessions:

```bash
orche list
```

Rules:

- prefer `orche whoami` over inferring from repo name, cwd, or tmux pane ids manually
- do not assume the current supervisor session is called `orche` unless `whoami`, `list`, or the user explicitly establishes that
- if the established current session is `orche`, then `tmux:orche` is the correct tmux notify target
- if you cannot establish the current session, do not invent a tmux notify target

## Operating Rules

### Prefer handoff over live babysitting

After `orche prompt`, do not keep polling by default.

Only inspect the worker when:

- the user asked for progress
- the worker likely needs input
- you received a notify and need details
- you are preparing the next prompt

### Prefer `status` before `read`

Use `status` first to answer:

- is the pane still alive?
- is the agent still running?
- is there a pending turn?
- is watchdog reporting `running`, `stalled`, or `needs-input`?

Then use `read` for the transcript.

### Only use `input` / `key` for real interactive prompts

Use:

```bash
orche input repo-worker "yes"
orche key repo-worker Enter
```

This is for cases like:

- approval prompts
- shell confirmations
- blocked interactive questions

Do not use `input` as a substitute for `prompt`.

### `attach` is for human takeover or deep debugging

If you need to directly take over the terminal:

```bash
orche attach repo-worker
```

Prefer `read` and `status` first. Use `attach` when you actually need the live TTY.

## Notify

Notify is explicit. There is no default route.

`open --notify` accepts:

- `tmux:<target-session>`
- `discord:<channel-id>`

Examples:

```bash
orche open --cwd /repo --agent codex --name repo-reviewer --notify discord:123456789012345678
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer
```

Rules:

- use `tmux:<session>` for agent-to-agent routing
- use `discord:<channel-id>` only when the user explicitly wants Discord delivery
- do not assume any global Discord config should be used automatically
- when you are delegating from one live `orche` session to another, set the worker notify target to the session returned by `orche whoami`
- if notify routing matters, prefer a managed session opened with `orche open --notify ...` instead of a native shortcut session

`tmux` maps to the built-in `tmux-bridge` provider internally.

## Managed vs Native Sessions

### Managed session

Use managed mode when you want `orche` to own the session lifecycle and notify binding:

```bash
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer
```

Managed sessions are the default choice for delegation.

### Native session

Use native mode when you need raw agent CLI args after `--`:

```bash
orche open --cwd /repo --agent claude -- --print --help
```

Rules:

- raw agent args must come after `--`
- native sessions do not take `--notify`
- do not combine raw agent args with `--notify`
- use `orche codex` / `orche claude` or native `open` only for ad-hoc interactive work, not for workers that must report back through notify

## Choosing the Right Open Command

Use managed open when you need a named worker with an explicit return path:

```bash
current_session="$(orche whoami)"
orche open --cwd /repo --agent codex --name repo-worker --notify "tmux:${current_session}"
```

Use a native shortcut only when no notify binding is needed:

```bash
orche codex --model gpt-5.4
```

Practical default:

- if the worker should report back, use `orche open --notify ...`
- if you just want to enter a fresh agent terminal yourself, use `orche codex` or `orche claude`

## Multi-Session Pattern

Reviewer/worker is the standard pattern:

```bash
# reviewer session
orche open --cwd /repo --agent codex --name repo-reviewer --notify discord:123456789012345678

# worker reports back to reviewer through tmux
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer

# send implementation work
orche prompt repo-worker "implement the parser refactor"

# later inspect reviewer
orche read repo-reviewer --lines 120
```

For multiple workers:

- give every session a stable name
- route workers back to one reviewer session
- keep prompts self-contained
- inspect only the sessions relevant to the next decision

## Recovery

If the agent is stuck but the session should survive:

```bash
orche cancel repo-worker
```

Then inspect:

```bash
orche status repo-worker
orche read repo-worker --lines 120
```

If the work is finished or the session is no longer useful:

```bash
orche close repo-worker
```

## Anti-Patterns

Avoid these:

- opening a new session for every tiny follow-up instead of reusing one
- combining native raw agent args with `--notify`
- using `input` for normal task prompts
- attaching to every worker when `status` or `read` would be enough
- relying on implicit global notify behavior
- polling continuously after `prompt` without a concrete reason

## Quick Reference

```bash
# create or reuse a named managed session
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer

# create or reuse a native interactive session
orche open --cwd /repo --agent claude -- --print --help

# send work
orche prompt repo-worker "analyze the failing tests"

# inspect
orche status repo-worker
orche read repo-worker --lines 80
orche list

# answer a prompt
orche input repo-worker "y"
orche key repo-worker Enter

# take over
orche attach repo-worker

# interrupt current turn
orche cancel repo-worker

# end session
orche close repo-worker
```
