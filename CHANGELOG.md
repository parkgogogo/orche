# Changelog

## v0.4.2 - 2026-04-02

- Sync project `trust_level = "trusted"` into the source Codex `config.toml` before cloning managed homes, with atomic writes and a backup file to avoid trust prompt regressions.
- Preserve top-level `notify` handling while refreshing managed Codex homes from the current source config on every reuse.
- Add regression coverage for trust sync, source-config backup behavior, invalid TOML protection, and managed-home refresh behavior.
- Add `sessions list` and `sessions clearall` commands.
- Keep Codex `notify` at the top level of generated `config.toml`.
