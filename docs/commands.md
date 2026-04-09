# Command Reference

## Core Commands

- `orche open`
  Create or reuse a named control endpoint.

- `orche codex` / `orche claude`
  Open a fresh native session for the current directory and attach immediately.

- `orche prompt`
  Delegate work into an existing session.

- `orche status`
  Check whether the pane and agent are alive, and whether a turn is pending.

- `orche read`
  Inspect recent terminal output without taking over the TTY.

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

## CLI Entry Shortcuts

Use the short flags on CLI entry surfaces:

```bash
orche -h
orche -v
orche config -h
```

Notes:

- `-h` is supported on the root command and command groups
- `-v` is supported on the root command only
- leaf commands still use `--help`, for example `orche attach --help`

## Managed vs Native Sessions

### Managed session

Use managed mode for normal orchestration:

```bash
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer
```

This is the default recommendation because `orche` can manage session metadata and routing coherently.

### Native session

Use native mode when you need raw agent CLI args:

```bash
orche open --cwd /repo --agent claude -- --print --help
```

Rules:

- raw agent args must come after `--`
- native sessions do not use `--notify`
- do not mix raw agent args with managed notify routing
