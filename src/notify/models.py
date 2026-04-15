from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NotifyEvent:
    event: str
    summary: str
    session: str
    status: str
    cwd: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedRoute:
    provider: str
    target: str = ""
    session: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeliveryResult:
    provider: str
    ok: bool
    detail: str = ""
    target: str = ""
