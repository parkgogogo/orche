from __future__ import annotations

from abc import ABC, abstractmethod

from .models import DeliveryResult, NotifyEvent, ResolvedRoute


class Notifier(ABC):
    name = "unknown"

    @abstractmethod
    def send(self, event: NotifyEvent, route: ResolvedRoute) -> DeliveryResult:
        raise NotImplementedError
