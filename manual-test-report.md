# Manual Test Report

Date: 2026-04-03
Branch: `feature/merge-pluggable-agents`

## Scope

This report covers the real command-line scenarios described in `test.md`, without using `pytest` as the primary validation path.

Covered scenarios:

1. Basic native shortcut workflow with repeated `orche codex`
2. Multi-session collaboration where session A reads `SKILL.md`, creates session B, sends a message, and verifies `tmux-bridge` notify back to A

## Environment

- `orche`: `/Users/dnq/.local/bin/orche`
- `tmux`: `/opt/homebrew/bin/tmux`
- `codex`: `/opt/homebrew/bin/codex`
- `tmux-bridge`: `~/.smux/bin/tmux-bridge`

## Scenario One

### Goal

Run `orche codex` multiple times and verify:

- each native session starts and remains usable
- native shortcut sessions are operationally equivalent to `session-new` sessions for session identity, status, read, and send
- key differences remain:
  - native shortcut opens interactive tmux flow
  - native shortcut has no notify binding
  - native shortcut does not use managed runtime settings

### Commands Used

```bash
TERM=xterm-256color orche codex --cwd /Users/dnq/.openclaw/workspace/repo/orche --session-name manual-codex-b
TERM=xterm-256color orche codex --cwd /Users/dnq/.openclaw/workspace/repo/orche --session-name manual-codex-c

orche status --session manual-codex-b
orche status --session manual-codex-c

orche session-new \
  --cwd /Users/dnq/.openclaw/workspace/repo/orche \
  --agent codex \
  --name manual-managed-compare \
  --notify-to discord \
  --notify-target 1111111111

orche status --session manual-managed-compare
orche send --session manual-codex-b "收到请回复 native-b"
orche send --session manual-managed-compare "收到请回复 managed"
orche read --session manual-codex-b --lines 80
orche read --session manual-managed-compare --lines 80
```

### Observations

- `manual-codex-b` and `manual-codex-c` both launched successfully as native sessions.
- Both native sessions showed:
  - `Running: yes`
  - `Pane exists: yes`
  - correct repo `CWD`
- `manual-managed-compare` launched successfully as a managed session.
- The managed session showed additional managed-only metadata:
  - `CODEX_HOME`
  - `Managed: yes`
  - `Discord session`
  - `Notify binding`
- `orche send` worked for both:
  - native session replied with `native-b`
  - managed session replied with `managed`

### Result

Pass.

Native shortcut sessions are usable and equivalent to managed sessions for core session lifecycle and prompt delivery. The expected differences are present: native sessions are interactive tmux-first and do not carry managed notify/runtime metadata.

### Issue Found

When running `orche codex` in a tmux-marked environment without an active tmux client, `attach_session()` attempted `tmux switch-client -t orche-smux` and failed with:

```text
no current client
```

### Fix Applied

`src/backend.py` was updated so `attach_session()` now:

1. tries `switch-client` when `TMUX` is set
2. falls back to `attach-session` if `switch-client` fails

This fixed the native shortcut path for the tested environment.

## Scenario Two

### Goal

Validate that a real Codex session A can:

1. read `SKILL.md`
2. use the documented `orche` workflow correctly
3. create session B
4. send B the exact message:
   `您好 codex，如果收到消息，请回复 hello`
5. observe a `tmux-bridge` notify from B back to A

### Commands Used

```bash
orche session-new \
  --cwd /Users/dnq/.openclaw/workspace/repo/orche \
  --agent codex \
  --name manual-s2-a \
  --notify-to discord \
  --notify-target 1111111111

orche send --session manual-s2-a "Read SKILL.md in the current repo first and follow its documented orche workflow. Then create a new managed codex session named manual-s2-b with --notify-to tmux-bridge --notify-target manual-s2-a. After creating session B, send this exact message to it: 您好 codex，如果收到消息，请回复 hello. Then wait and verify whether session A receives session B's notify reply. In your own output, clearly report each step result: SKILL.md read, session B created, message sent, reply received or not received."

orche read --session manual-s2-a --lines 320
orche status --session manual-s2-b
orche read --session manual-s2-b --lines 220
```

### Observations

Session A explicitly reported these steps in its own output:

- `SKILL.md` was found and read
- the documented `session-new` and `send` workflow was understood
- `manual-s2-b` was created with:
  - `--notify-to tmux-bridge`
  - `--notify-target manual-s2-a`
- the exact Chinese message was sent to session B
- A received a notify payload back from B

Observed notify in session A:

```text
orche notify
  source session: manual-s2-b
  status: success
  cwd: /Users/dnq/.openclaw/workspace/repo/orche

  hello
```

Observed session B output:

```text
› 您好 codex，如果收到消息，请回复 hello.

• hello
```

Observed session B status:

- `Running: yes`
- `Managed: yes`
- `Notify binding: {"provider": "tmux-bridge", "target": "manual-s2-a"}`

### Result

Pass.

The real session-to-session collaboration flow worked end to end:

- A followed `SKILL.md`
- A created B correctly
- A sent the exact message to B
- B replied with `hello`
- `tmux-bridge` delivered B's completion notify back into A

## Overall Summary

- Scenario one: pass
- Scenario two: pass
- Real issue found during manual testing: native shortcut attach fallback
- Issue was fixed in code and validated afterward

## Follow-Up

The tested manual sessions were closed after verification:

- `manual-codex-a`
- `manual-codex-b`
- `manual-codex-c`
- `manual-managed-compare`
- `manual-s2-a`
- `manual-s2-b`
