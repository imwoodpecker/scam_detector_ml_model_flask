"""
engine.py

Offline, deterministic, explainable scam-intent detection engine.

Design goals:
- Streaming-friendly: partial utterances arrive over time (chunks)
- Privacy-first: no external APIs, no ML, no remote calls
- Auditable: each risk point is attributable to a rule with evidence
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scorer import Assessment, assess_text
from timeline import Timeline


@dataclass
class EngineState:
    """
    Session-scoped state for streaming analysis.
    Keep it serializable so Android can persist/restore if desired.
    """

    session_id: str = "default"
    # Rolling transcript (you can cap this if desired)
    transcript: str = ""
    # Count how many chunks we've processed
    chunk_index: int = 0
    # Timeline of behavioral events
    timeline: Timeline = field(default_factory=Timeline)

    def __post_init__(self) -> None:
        # Ensure timeline session_id matches state
        self.timeline.session_id = self.session_id


class ScamIntentEngine:
    """
    Main entry point for the Android app.
    Create one instance per conversation/session.
    """

    def __init__(self, session_id: str = "default") -> None:
        self.state = EngineState(session_id=session_id, timeline=Timeline(session_id=session_id))

    def ingest(self, text_chunk: str, *, is_final: bool = False) -> Assessment:
        """
        Ingest a new partial utterance chunk and return a full assessment.

        Notes:
        - We keep analysis deterministic by evaluating rules over the current transcript.
        - For streaming safety, rules should tolerate mid-word chunks.
        """

        chunk = text_chunk or ""
        self.state.chunk_index += 1

        # Append with a separator to avoid accidental word-joins between chunks.
        if self.state.transcript and not self.state.transcript.endswith((" ", "\n", "\t")):
            self.state.transcript += " "
        self.state.transcript += chunk

        self.state.timeline.add("chunk_ingested", detail=f"i={self.state.chunk_index},len={len(chunk)}")

        assessment = assess_text(
            self.state.transcript,
            timeline=self.state.timeline,
            chunk_index=self.state.chunk_index,
            is_final=is_final,
        )
        return assessment

