"""
timeline.py

Very small "behavioral tracking" helper. This is intentionally lightweight and
in-memory. You can later persist events per session to disk or a database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time


@dataclass
class Event:
    ts: float
    kind: str
    detail: str | None = None


@dataclass
class Timeline:
    session_id: str = "default"
    events: list[Event] = field(default_factory=list)

    def add(self, kind: str, detail: str | None = None) -> None:
        self.events.append(Event(ts=time(), kind=kind, detail=detail))

    def count(self, kind: str) -> int:
        return sum(1 for e in self.events if e.kind == kind)

    def last_n(self, n: int) -> list[Event]:
        if n <= 0:
            return []
        return self.events[-n:]

