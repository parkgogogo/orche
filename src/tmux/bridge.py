from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Optional, Union

from tmux.client import tmux
from tmux.query import list_panes, pane_exists, read_pane


def _resolve_bridge_pane(session: str, fallback_pane_id: str = "") -> str:
    session_name = str(session or "").strip()
    if not session_name:
        raise RuntimeError("session is required")
    for pane in list_panes():
        if str(pane.get("pane_title") or "").strip() == session_name:
            return str(pane.get("pane_id") or "").strip()
    resolved_fallback_pane_id = str(fallback_pane_id or "").strip()
    if resolved_fallback_pane_id and pane_exists(resolved_fallback_pane_id):
        return resolved_fallback_pane_id
    raise RuntimeError(f"Unknown session: {session_name}")


def bridge_name_pane(pane_id: str, session: str) -> None:
    tmux("select-pane", "-t", pane_id, "-T", session, check=True, capture=True)


def bridge_resolve(session: str, *, fallback_pane_id: str = "") -> Optional[str]:
    try:
        return _resolve_bridge_pane(session, fallback_pane_id)
    except Exception:
        return None


def bridge_read(session: str, lines: int = 200, *, fallback_pane_id: str = "") -> str:
    pane_id = _resolve_bridge_pane(session, fallback_pane_id)
    return read_pane(pane_id, max(lines, 1)).rstrip("\n")


def bridge_type(session: str, text: str, *, fallback_pane_id: str = "") -> None:
    if text:
        pane_id = _resolve_bridge_pane(session, fallback_pane_id)
        buffer_name = f"orche-{uuid.uuid4().hex}"
        try:
            tmux(
                "load-buffer",
                "-b",
                buffer_name,
                "-",
                check=True,
                capture=True,
                input_text=text,
            )
            tmux(
                "paste-buffer",
                "-t",
                pane_id,
                "-b",
                buffer_name,
                check=True,
                capture=True,
            )
        finally:
            tmux("delete-buffer", "-b", buffer_name, check=False, capture=True)


def bridge_keys(
    session: str, keys: Union[Iterable[str], str], *, fallback_pane_id: str = ""
) -> None:
    values = [keys] if isinstance(keys, str) else list(keys)
    if values:
        pane_id = _resolve_bridge_pane(session, fallback_pane_id)
        tmux("send-keys", "-t", pane_id, *values, check=True, capture=True)
