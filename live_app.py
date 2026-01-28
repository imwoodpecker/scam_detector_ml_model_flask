"""
live_app.py

PC runner that simulates the full production pipeline:
stdin (simulated STT chunks) -> streaming scam engine -> live HUD popup -> final YAML report

Why stdin?
- Microphone capture + offline STT engines are platform-specific and often require native deps.
- This keeps the intelligence engine + HUD logic testable and deterministic on any PC.
"""

from __future__ import annotations

import argparse
import sys
import threading
from queue import Queue

from audio_listener import TextChunkSource
from scorer import StreamingScorer
from stt_rules import assess_stt_quality

try:
    # Optional; only used when --hud is enabled.
    from hud import HudController, HudState
    from hud_messages import pick_reason
except Exception:  # pragma: no cover
    HudController = None  # type: ignore[assignment]
    HudState = None  # type: ignore[assignment]
    pick_reason = None  # type: ignore[assignment]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Live runner (PC): stdin -> streaming engine (+ optional HUD) -> final YAML.")
    p.add_argument(
        "--hud",
        action="store_true",
        help="Enable the non-intrusive desktop HUD popup. Disabled by default.",
    )
    return p.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    scorer = StreamingScorer(session_id="pc")
    hud = None
    q: Queue = Queue()
    if args.hud:
        if HudController is None:
            raise SystemExit("HUD requested but tkinter HUD is unavailable in this environment.")
        hud = HudController()
        hud.poll_queue(q)  # type: ignore[arg-type]

    source = TextChunkSource(chunk_ms=2000)

    def worker() -> None:
        # Feed chunks from stdin; enqueue HUD updates after each chunk.
        for chunk in source.iter_chunks_from_lines(sys.stdin):
            sttq = assess_stt_quality(chunk.text)

            snap = scorer.ingest_chunk(chunk.text)
            if sttq.tier in ("low", "partial"):
                # Soft dampening for unclear text; deterministic and traceable.
                scorer.ingest_chunk("reference number")
                snap = scorer.ingest_chunk("")

            if hud is not None:
                reason = pick_reason(snap.newly_detected_signals, snap.risk_level)  # type: ignore[misc]
                q.put(HudState(risk_score=snap.risk_score, risk_level=snap.risk_level, reason=reason))  # type: ignore[misc]

            # Console snapshot (YAML-ish)
            print(f"- chunk: {snap.chunk_index}")
            print(f"  risk_score: {snap.risk_score}")
            print(f"  risk_level: {snap.risk_level}")
            print(f"  newly_detected_signals: {snap.newly_detected_signals or []}")
            if sttq.reasons:
                print(f"  stt_quality: {sttq.tier}")
                print(f"  stt_reasons: {sttq.reasons}")

        final = scorer.finalize()
        print("final_report:")
        print(f"  risk_score: {final.risk_score}")
        print(f"  risk_level: {final.risk_level}")
        print("  signals:")
        for s in final.signals:
            print(f"    - {s}")
        print("  explanation:")
        for t in final.trace:
            print(f"    - chunk {t.chunk_index}: {t.rule_id} {t.change:+d} ({t.why})")
        print("  audit_notes:")
        print("    - No audio/text leaves the device. All decisions are deterministic and traceable.")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    if hud is not None:
        hud.loop()
    else:
        # Console-only mode: wait until input completes.
        t.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

