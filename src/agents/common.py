from __future__ import annotations

import contextlib
import re
import shutil
import tempfile
import uuid
from pathlib import Path

from notify_hook import NOTIFY_DISCORD_SH


DEFAULT_RUNTIME_HOME_ROOT = Path(tempfile.gettempdir())


def normalize_runtime_home(runtime_home: str | Path | None) -> str:
    if runtime_home in (None, ""):
        return ""
    return str(Path(str(runtime_home)).expanduser().resolve())


def session_key(session: str) -> str:
    lowered = []
    for ch in session.lower():
        if ch.isalnum():
            lowered.append(ch)
        elif ch in ("-", "_", "/", "."):
            lowered.append("-")
    value = "".join(lowered)
    while "--" in value:
        value = value.replace("--", "-")
    return value.strip("-") or "root"


def validate_discord_channel_id(value: str) -> str:
    channel_id = re.sub(r"\s+", "", value or "")
    if not channel_id or not channel_id.isdigit():
        raise ValueError("--discord-channel-id must be a numeric Discord channel ID")
    return channel_id


def write_text_atomically(path: Path, content: str, *, backup_path: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    try:
        if backup_path is not None and path.exists():
            shutil.copy2(path, backup_path)
        temp_path.replace(path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()


def remove_runtime_home(runtime_home: str | Path) -> None:
    normalized = Path(normalize_runtime_home(runtime_home))
    candidates: list[Path] = []
    for candidate in (normalized, normalized.resolve()):
        if candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        if candidate.exists():
            shutil.rmtree(candidate, ignore_errors=True)


def write_notify_hook(hook_path: Path) -> None:
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(NOTIFY_DISCORD_SH, encoding="utf-8")
    hook_path.chmod(0o755)
