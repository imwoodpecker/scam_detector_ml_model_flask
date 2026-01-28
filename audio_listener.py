"""
audio_listener.py

Platform-agnostic audio capture interface.

PC testing:
- We provide a TextChunkSource that simulates "audio->stt" by reading stdin lines.

Android migration:
- Replace the implementation with AudioRecord-based capture feeding the same ChunkSink.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass(frozen=True)
class AudioFrame:
    """
    Raw audio frame (PCM bytes) plus monotonically increasing timestamps.

    We do NOT use wall-clock time; we use sample-index derived time so it's deterministic
    and testable (and doesn't leak real timestamps).
    """

    t0_ms: int
    t1_ms: int
    pcm16le: bytes
    sample_rate_hz: int
    channels: int


@dataclass(frozen=True)
class TextChunk:
    """
    Output of STT for a short time window (1–3 seconds).
    """

    t0_ms: int
    t1_ms: int
    text: str
    stt_tier: str  # "high" | "medium" | "low" | "partial"


class ChunkSink(Protocol):
    def on_chunk(self, chunk: TextChunk) -> None: ...

    def on_end(self) -> None: ...


class TextChunkSource:
    """
    PC test harness: treat each input line as a "chunk" with deterministic timestamps.
    This lets you test the full pipeline (engine + HUD) without mic/STT dependencies.
    """

    def __init__(self, *, chunk_ms: int = 2000) -> None:
        self._chunk_ms = chunk_ms
        self._t_ms = 0

    def iter_chunks_from_lines(self, lines: Iterable[str]) -> Iterable[TextChunk]:
        for line in lines:
            text = (line or "").strip()
            if not text:
                continue
            t0 = self._t_ms
            t1 = self._t_ms + self._chunk_ms
            self._t_ms = t1
            # For PC simulation we mark as "high". Real STT will compute tier deterministically.
            yield TextChunk(t0_ms=t0, t1_ms=t1, text=text, stt_tier="high")

