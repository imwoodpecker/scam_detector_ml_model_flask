"""
watch_audio_folder.py

Drop-folder runner:
- Put .mp3 or .wav files into ./audio_inbox/
- This script detects new files, runs audio_risk_pipeline.analyze_audio(),
  writes results to ./audio_outbox/<name>.json
- Moves processed audio to ./audio_inbox/processed/ (or ./audio_inbox/failed/)

Offline notes:
- .mp3 requires ffmpeg in PATH OR convert to wav first.
- STT backend must be installed (faster-whisper, whisper, or vosk + local model).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass

from audio_risk_pipeline import analyze_audio
from notifier import notify_risk


@dataclass(frozen=True)
class Config:
    inbox_dir: str
    outbox_dir: str
    poll_seconds: float
    stable_seconds: float


def _is_audio(name: str) -> bool:
    n = name.lower()
    return n.endswith(".wav") or n.endswith(".mp3")


def _ensure_dirs(cfg: Config) -> tuple[str, str, str]:
    inbox = os.path.abspath(cfg.inbox_dir)
    outbox = os.path.abspath(cfg.outbox_dir)
    processed = os.path.join(inbox, "processed")
    failed = os.path.join(inbox, "failed")
    os.makedirs(inbox, exist_ok=True)
    os.makedirs(outbox, exist_ok=True)
    os.makedirs(processed, exist_ok=True)
    os.makedirs(failed, exist_ok=True)
    return inbox, outbox, processed, failed


def _stable_file(path: str, stable_seconds: float) -> bool:
    """
    Avoid processing a file while it is still being copied into the folder.
    Deterministic: size must remain constant over stable_seconds.
    """

    try:
        s1 = os.path.getsize(path)
    except OSError:
        return False
    time.sleep(stable_seconds)
    try:
        s2 = os.path.getsize(path)
    except OSError:
        return False
    return s1 == s2 and s2 > 0


def _write_json(out_path: str, obj: dict) -> None:
    # Windows/OneDrive can briefly lock files; use unique temp names + retries.
    last_err: Exception | None = None
    for _attempt in range(6):
        tmp = f"{out_path}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            os.replace(tmp, out_path)
            return
        except Exception as e:
            last_err = e
            try:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            except OSError:
                pass
            time.sleep(0.25)
    raise last_err  # type: ignore[misc]


def run(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Watch ./audio_inbox for audio files and analyze them offline.")
    p.add_argument("--inbox", default="audio_inbox", help="Folder to drop .wav/.mp3 files into.")
    p.add_argument("--outbox", default="audio_outbox", help="Folder where JSON results are written.")
    p.add_argument("--poll", type=float, default=1.0, help="Polling interval in seconds.")
    p.add_argument("--stable", type=float, default=1.0, help="Seconds to wait to ensure file copy is complete.")
    args = p.parse_args(argv)

    cfg = Config(inbox_dir=args.inbox, outbox_dir=args.outbox, poll_seconds=args.poll, stable_seconds=args.stable)
    inbox, outbox, processed, failed = _ensure_dirs(cfg)

    print(f"Watching inbox: {inbox}")
    print(f"Writing results to: {outbox}")
    print("Drop .wav/.mp3 files into the inbox. Ctrl+C to stop.")

    seen: set[str] = set()
    while True:
        try:
            names = os.listdir(inbox)
        except OSError:
            time.sleep(cfg.poll_seconds)
            continue

        for name in names:
            if name in ("processed", "failed"):
                continue
            if not _is_audio(name):
                continue

            path = os.path.join(inbox, name)
            if path in seen:
                continue
            if not os.path.isfile(path):
                continue
            if not _stable_file(path, cfg.stable_seconds):
                continue

            seen.add(path)
            base = os.path.splitext(os.path.basename(name))[0]
            out_path = os.path.join(outbox, base + ".json")

            print(f"Analyzing: {name}")
            try:
                result = analyze_audio(path)
                _write_json(out_path, result)
                # Live desktop hint with risk number & type.
                try:
                    notify_risk(
                        float(result.get("risk_score", 0.0)),
                        str(result.get("risk_level", "")),
                        summary=str(result.get("summary", "")),
                    )
                except Exception:
                    # Notification is best-effort; never break analysis.
                    pass
                shutil.move(path, os.path.join(processed, name))
                print(f"OK: wrote {os.path.basename(out_path)}")
            except Exception as e:
                err = {"error": str(e), "file": name}
                _write_json(os.path.join(outbox, base + ".error.json"), err)
                try:
                    shutil.move(path, os.path.join(failed, name))
                except OSError:
                    pass
                print(f"FAILED: {name} ({e})")

        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        raise SystemExit(0)

