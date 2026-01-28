"""
stt/diarizer.py

Deterministic 2-speaker diarization for transcript segments.

Important: This is NOT ML diarization. It's a production-friendly, offline,
auditable heuristic that assigns segments to two speakers based on turn-taking.

Assumption:
- For many phone calls, speakers alternate turns separated by short pauses.

Algorithm:
- Merge segments into "turns" when gaps are small (<= gap_threshold_s).
- Alternate speaker assignment per turn: SPEAKER_1, SPEAKER_2, ...
- Expand back to segments with speaker labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict


Speaker = Literal["SPEAKER_1", "SPEAKER_2"]


class DiarizedSegment(TypedDict):
    start: float
    end: float
    speaker: Speaker
    text: str


class Segment(TypedDict):
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class DiarizerConfig:
    gap_threshold_s: float = 0.8
    min_turn_s: float = 0.4
    start_speaker: Speaker = "SPEAKER_1"


def diarize_segments(segments: list[Segment], config: DiarizerConfig | None = None) -> list[DiarizedSegment]:
    cfg = config or DiarizerConfig()
    if not segments:
        return []

    segs = sorted(segments, key=lambda s: (float(s["start"]), float(s["end"])))
    out: list[DiarizedSegment] = []

    # Build turns as ranges of segment indices.
    turns: list[tuple[int, int]] = []
    start_i = 0
    for i in range(1, len(segs)):
        prev = segs[i - 1]
        cur = segs[i]
        gap = float(cur["start"]) - float(prev["end"])
        if gap > cfg.gap_threshold_s:
            turns.append((start_i, i - 1))
            start_i = i
    turns.append((start_i, len(segs) - 1))

    # Assign speakers alternately per turn.
    speaker = cfg.start_speaker
    for a, b in turns:
        # If a turn is extremely short, we still keep it deterministic; no reassignment.
        for i in range(a, b + 1):
            s = segs[i]
            out.append(
                {
                    "start": float(s["start"]),
                    "end": float(s["end"]),
                    "speaker": speaker,
                    "text": str(s["text"]),
                }
            )
        speaker = "SPEAKER_2" if speaker == "SPEAKER_1" else "SPEAKER_1"

    return out

