# Skills Guide

Skills extend what your agents can do when running under `orche`. A skill is typically a set of specialized instructions, tools, or workflows that the agent can reference during its session.

## Installing a Skill

Skills are loaded by the underlying agent (Codex, Claude, or OpenClaw), not by `orche` itself. To install a skill:

1. Copy the skill folder to the agent's skills directory:
   - **Codex**: `~/.codex/skills/<skill-name>/`
   - **Claude**: `~/.claude/skills/<skill-name>/` (or your configured Claude home)
   - **OpenClaw**: `~/.openclaw/skills/<skill-name>/`

2. Ensure the skill contains at minimum a `SKILL.md` file.

3. Restart the agent session for the skill to be picked up.

## Bundled Skills

The `tmux-orche` repository includes a few example skills under the `skills/` directory:

- `codex-claude/` — Common workflows for Codex and Claude integration
- `openclaw/` — OpenClaw-specific supervision and routing patterns

You can copy these directly into your agent's skills directory.
