"""Process audio files and delete originals after analysis."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass

from audio_risk_pipeline import analyze_audio


@dataclass(frozen=True)
class Config:
    inbox_dir: str
    outbox_dir: str


def _is_audio(name: str) -> bool:
    return name.lower().endswith((".wav", ".mp3"))


def _write_json(path: str, obj: dict) -> None:
    last_err: Exception | None = None
    for _attempt in range(6):
        tmp = f"{path}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
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
    p = argparse.ArgumentParser(description="Process audio inbox once and exit.")
    p.add_argument("--inbox", default="audio_inbox")
    p.add_argument("--outbox", default="audio_outbox")
    args = p.parse_args(argv)

    cfg = Config(inbox_dir=args.inbox, outbox_dir=args.outbox)
    inbox = os.path.abspath(cfg.inbox_dir)
    outbox = os.path.abspath(cfg.outbox_dir)
    processed = os.path.join(inbox, "processed")
    failed = os.path.join(inbox, "failed")
    os.makedirs(inbox, exist_ok=True)
    os.makedirs(outbox, exist_ok=True)
    os.makedirs(processed, exist_ok=True)
    os.makedirs(failed, exist_ok=True)

    files = [f for f in os.listdir(inbox) if _is_audio(f) and os.path.isfile(os.path.join(inbox, f))]
    if not files:
        print(f"No audio files found in {inbox}")
        return 0

    for name in sorted(files):
        src = os.path.join(inbox, name)
        base = os.path.splitext(name)[0]
        out_path = os.path.join(outbox, base + ".json")
        print(f"Analyzing: {name}")
        try:
            result = analyze_audio(src)
            _write_json(out_path, result)
            # Delete original audio file after successful processing
            try:
                os.remove(src)
                print(f"Deleted original audio file: {name}")
            except OSError as e:
                print(f"Warning: Could not delete {name}: {e}")
                try:
                    shutil.move(src, os.path.join(processed, name))
                except OSError:
                    pass
            print(f"OK: {os.path.basename(out_path)}")
        except Exception as e:
            err = {"error": str(e), "file": name}
            _write_json(os.path.join(outbox, base + ".error.json"), err)
            try:
                os.remove(src)
                print(f"Deleted failed audio file: {name}")
            except OSError as e:
                print(f"Warning: Could not delete failed file {name}: {e}")
                try:
                    shutil.move(src, os.path.join(failed, name))
                except OSError:
                    pass
            print(f"FAILED: {name} ({e})")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())

