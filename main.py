"""
Entry point for Scam Shield Model.

Run:
  python main.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from dataclasses import asdict

from process_audio_inbox_once import run as process_inbox_once_run
from watch_audio_folder import run as watch_folder_run
from web_ui import main as web_ui_main
from live_app import run as live_app_run
from scorer import (
    Assessment,
    FinalReport,
    RiskReport,
    StreamingScorer,
    StreamingSnapshot,
    score_text,
)
from timeline import Timeline


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Scam Shield Model (simple heuristic scorer).")
    p.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Text to score. If omitted, reads from STDIN.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print output as JSON.",
    )
    p.add_argument(
        "--session",
        default="default",
        help="Session id for behavioral timeline tracking.",
    )
    p.add_argument(
        "--stream",
        action="store_true",
        help="Read streaming chunks (one per line) from STDIN and print an updated assessment after each chunk.",
    )
    p.add_argument(
        "--yaml",
        action="store_true",
        help="Print YAML-style output (default for streaming final report).",
    )
    p.add_argument(
        "--audio-inbox",
        action="store_true",
        help="Process ./audio_inbox once (audio -> STT -> risk) and write results to ./audio_outbox.",
    )
    p.add_argument(
        "--open-results",
        action="store_true",
        help="After processing audio inbox, open the newest result JSON in your default browser.",
    )
    p.add_argument(
        "--watch",
        action="store_true",
        help="Watch audio_inbox continuously (drop-folder mode).",
    )
    p.add_argument(
        "--web",
        action="store_true",
        help="Start the local web UI (http://127.0.0.1:8000/).",
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="Run live stdin->engine pipeline (like live_app.py).",
    )
    p.add_argument(
        "--hud",
        action="store_true",
        help="Used with --live to enable the desktop HUD popup.",
    )
    return p


def _print_snapshot_yaml(s: StreamingSnapshot) -> None:
    print(f"- chunk: {s.chunk_index}")
    print(f"  risk_score: {s.risk_score}")
    print(f"  risk_level: {s.risk_level}")
    print(f"  score_delta: {s.score_delta}")
    print("  newly_detected_signals:")
    if s.newly_detected_signals:
        for sig in s.newly_detected_signals:
            print(f"    - {sig}")
    else:
        print("    - []")


def _print_final_yaml(r: FinalReport) -> None:
    print("final_report:")
    print(f"  risk_score: {r.risk_score}")
    print(f"  risk_level: {r.risk_level}")
    print("  signals:")
    for s in r.signals:
        print(f"    - {s}")
    print("  trace:")
    for t in r.trace:
        print(f"    - chunk: {t.chunk_index}")
        print(f"      rule: {t.rule_id}")
        print(f"      change: {t.change}")
        print(f"      why: {t.why}")


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    # App-mode shortcuts (single entry point for all runners).
    if args.web:
        return int(web_ui_main() or 0)
    if args.watch:
        # Run the watcher with its own CLI defaults.
        return int(watch_folder_run([]) or 0)
    if args.live:
        # Delegate to live_app runner; forward --hud
        live_argv: list[str] = []
        if args.hud:
            live_argv.append("--hud")
        return int(live_app_run(live_argv) or 0)

    # Default behavior: if no explicit text/stream given, process audio inbox.
    if not args.stream and args.text is None and not args.audio_inbox:
        args.audio_inbox = True

    if args.audio_inbox:
        # One-shot inbox processing.
        # (Keeps everything offline; requires a local STT backend + local model files.)
        rc = int(process_inbox_once_run(["--inbox", "audio_inbox", "--outbox", "audio_outbox"]) or 0)

        if args.open_results:
            try:
                out_dir = os.path.abspath("audio_outbox")
                candidates = [
                    os.path.join(out_dir, f)
                    for f in os.listdir(out_dir)
                    if f.lower().endswith(".json") and not f.lower().endswith(".error.json")
                ]
                if candidates:
                    newest = max(candidates, key=lambda p: os.path.getmtime(p))
                    webbrowser.open("file://" + newest.replace("\\", "/"))
            except Exception:
                # Opening is best-effort; never fail the analysis because of UI.
                pass

        return rc

    if args.stream:
        scorer = StreamingScorer(session_id=args.session)
        # Emit snapshots as YAML by default; JSON if requested.
        for line in sys.stdin:
            chunk = line.rstrip("\n")
            if not chunk.strip():
                continue
            snap = scorer.ingest_chunk(chunk)
            if args.json:
                print(json.dumps(asdict(snap), ensure_ascii=False))
            else:
                _print_snapshot_yaml(snap)
        final = scorer.finalize()
        if args.json:
            print(json.dumps(asdict(final), ensure_ascii=False))
        else:
            _print_final_yaml(final)
        return 0

    text = args.text
    if text is None:
        text = sys.stdin.read().strip()

    tl = Timeline(session_id=args.session)
    report: RiskReport = score_text(text, timeline=tl)

    if args.json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    else:
        print(f"risk_score: {report.risk_score}/100")
        print(f"risk_level: {report.risk_level}")
        if report.matched_phrases:
            print("matched_phrases:")
            for m in report.matched_phrases:
                print(f"  - {m}")
        if report.signals:
            print("signals:")
            for s in report.signals:
                print(f"  - {s}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

