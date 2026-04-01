# tmux-orche Installation Guide

This guide is written for agent-guided setup. Follow it top to bottom, verify each dependency, then install `tmux-orche`.

## 1. Check Dependencies

`tmux-orche` requires:

- `tmux`
- `tmux-bridge`
- `codex` CLI
- Python `3.9+`

### Check `tmux`

```bash
command -v tmux
tmux -V
```

If `tmux` is missing:

macOS with Homebrew:

```bash
brew install tmux
```

Ubuntu / Debian:

```bash
sudo apt update
sudo apt install -y tmux
```

Fedora:

```bash
sudo dnf install -y tmux
```

### Check `tmux-bridge`

```bash
command -v tmux-bridge
```

If `tmux-bridge` is missing, install it using the official `smux` / `tmux-bridge` installation flow used in your environment. `tmux-orche` expects `tmux-bridge` either:

- on your `PATH`, or
- at `~/.smux/bin/tmux-bridge`

After installation, verify again:

```bash
command -v tmux-bridge || ls ~/.smux/bin/tmux-bridge
```

### Check `codex` CLI

```bash
command -v codex
codex --version
```

If `codex` is missing, install the official Codex CLI first, then log in if required:

```bash
codex login
```

Verify that Codex can start:

```bash
codex --help
```

### Check Python

```bash
python3 --version
```

If needed, install Python `3.9+` using your system package manager, Homebrew, `pyenv`, or your standard environment management tool.

## 2. Install tmux-orche

Choose one installation method.

### Option A: Install with `pip`

From PyPI:

```bash
python3 -m pip install tmux-orche
```

From a local checkout:

```bash
python3 -m pip install .
```

### Option B: Install with `uv`

As a global tool:

```bash
uv tool install tmux-orche
```

From a local checkout:

```bash
uv tool install .
```

Into the current Python environment:

```bash
uv pip install .
```

### Option C: Install from source

```bash
git clone https://github.com/parkgogogo/orche
cd orche
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install .
```

## 3. Quick Verification

Verify the CLI is on `PATH`:

```bash
command -v orche
orche --help
orche backend
```

Verify config commands work:

```bash
orche config list
```

Verify session creation help:

```bash
orche session-new --help
```

Optional package sanity check from source checkout:

```bash
python3 -m compileall src
```

## 4. Troubleshooting

### `orche: command not found`

The install location is not on `PATH`.

Check where the script was installed:

```bash
python3 -m pip show tmux-orche
python3 -m site --user-base
```

If you used `uv tool install`, ensure the uv tool bin directory is on `PATH`.

### `tmux is not installed`

Install `tmux`, then verify:

```bash
command -v tmux
tmux -V
```

### `tmux-bridge is not installed`

Install `tmux-bridge` using your environment's `smux` setup, then verify one of these works:

```bash
command -v tmux-bridge
ls ~/.smux/bin/tmux-bridge
```

### `codex is not installed`

Install the Codex CLI, then verify:

```bash
command -v codex
codex --help
```

### Codex starts but is not logged in

Log in first:

```bash
codex login
```

### Session creation fails

Check the runtime dependencies again:

```bash
command -v tmux
command -v tmux-bridge || ls ~/.smux/bin/tmux-bridge
command -v codex
```

Then check the session command directly:

```bash
orche session-new --cwd /path/to/repo --agent codex
```

### Managed `CODEX_HOME` problems

By default, `orche` creates per-session temporary Codex homes under `/tmp/orche-codex-<session>/`.

Inspect session status:

```bash
orche status --session <session>
```

If needed, close the session and recreate it:

```bash
orche close --session <session>
orche session-new --cwd /path/to/repo --agent codex
```

### Notify or config issues

Check the runtime config:

```bash
orche config list
cat ~/.config/orche/config.json
```

If you are debugging notify delivery, also check:

```bash
orche turn-summary --session <session>
```
