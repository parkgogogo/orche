---
name: orche-codex-claude
description: Use this skill when Codex or Claude is supervising another agent through `orche`, and the worker must report back to the current agent session through an explicit `tmux:<session>` notify route. It enforces `orche whoami`, managed session setup, and a fire-and-forget workflow instead of polling or live babysitting.
---

# orche for Codex and Claude

This skill is for one supervisor shape only:

- the current supervisor is Codex or Claude
- the supervisor itself is working inside an `orche`-managed tmux session
- the worker must report back to that agent session through tmux

Do not use this skill when OpenClaw is the supervisor and the return path is Discord. That is a different skill.

## Non-Negotiable Rules

- Treat `notify` as the return path. If the worker must report back, open it with explicit `--notify tmux:<target-session>`.
- Treat `prompt` as fire-and-forget. After `orche prompt`, continue your own turn instead of watching the worker live.
- Never guess the tmux notify target. Resolve it with `orche whoami` first.
- Use managed sessions for delegated workers. A delegated worker that must report back is not a native session.
- Create a session once, then reuse it through `prompt`, `status`, `read`, `attach`, `input`, `key`, `cancel`, or `close`. Do not call `open` again with the same explicit session name; that errors instead of reusing it.
- Use `attach` only for human takeover or deep debugging, not as the default inspection path.

## Session Awareness First

Before opening a worker or choosing a tmux notify target, determine whether you are already inside an `orche` session.

Start with:

```bash
orche whoami
```

Interpretation:

- if it returns a session name, that session is the safest default tmux notify target
- if it fails, do not invent a tmux target from repo name, cwd, or pane ids

If `whoami` fails but you still need context, inspect known sessions:

```bash
orche list
```

If you cannot establish the current supervisor session, do not open a tmux-routed worker yet.

## Default Workflow

Use this sequence unless the user explicitly wants something else:

```bash
# 1. resolve the current supervisor session
current_session="$(orche whoami)"

# 2. open a managed worker with an explicit tmux return path
orche open --cwd /repo --agent codex --name repo-worker --notify "tmux:${current_session}"

# 3. send work
orche prompt repo-worker "implement the parser refactor"

# 4. continue your own work
```

Later, inspect only if needed:

```bash
orche status repo-worker
orche read repo-worker --lines 120
```

Take over only if necessary:

```bash
orche attach repo-worker
```

## Notify Policy

Notify is mandatory for delegated reviewer/worker loops because it closes the control loop back to the supervisor session.

Rules:

- use `tmux:<session>` as the notify target
- prefer the session returned by `orche whoami`
- do not assume the current supervisor session is called `orche` unless `whoami`, `list`, or the user established that
- changing the notify target means opening a new session, not mutating the existing one
- do not combine raw agent CLI args after `--` with `--notify`

Managed session example:

```bash
current_session="$(orche whoami)"
orche open --cwd /repo --agent codex --name repo-worker --notify "tmux:${current_session}"
```

Native sessions are for ad-hoc interactive work and are not the default here:

```bash
orche codex --model gpt-5.4
```

## Inspection Discipline

Prefer `status` before `read`.

Use `status` to answer:

- is the pane alive
- is the agent running
- is there a pending turn
- is watchdog reporting `running`, `stalled`, or `needs-input`

Use `read` only when you need transcript detail.

Use `input` and `key` only for real interactive prompts:

```bash
orche input repo-worker "y"
orche key repo-worker Enter
```

Do not use `input` as a substitute for a normal task prompt.

## Recovery

If the worker is stuck but the session should survive:

```bash
orche cancel repo-worker
orche status repo-worker
orche read repo-worker --lines 120
```

If the work is finished or the session is no longer useful:

```bash
orche close repo-worker
```

## Anti-Patterns

Avoid these:

- guessing a tmux notify target instead of resolving it with `orche whoami`
- opening a worker without `--notify` when the result must return to the supervisor session
- polling continuously after `prompt`
- attaching to every worker when `status` or `read` would be enough
- using `input` for normal task delegation
- combining raw agent args with `--notify`
- opening a second session for every tiny follow-up instead of reusing the existing named session
