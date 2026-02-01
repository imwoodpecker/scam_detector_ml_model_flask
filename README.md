# scam_shield_model

Minimal file structure for a scam risk scorer.

## Files

- `main.py`: entry point (**run this**)
- `scorer.py`: risk scoring logic
- `phrase_bank.py`: scam phrases / keywords (your data knobs)
- `timeline.py`: simple behavioral tracking (in-memory)

## Run

```bash
python main.py "URGENT: Verify your account now! Click the link: https://example.com"
```

Or read from STDIN:

```bash
echo "Your account will be suspended. Verify now." | python main.py
```

JSON output:

```bash
python main.py --json "Claim your prize by sending bitcoin to this wallet"
```

## Audio file (drop-folder workflow)

### Single entry point (recommended)

By default, running `main.py` will **process `audio_inbox/` once** and write results to `audio_outbox/`:

```bash
python main.py
```

Open the newest result automatically:

```bash
python main.py --open-results
```

### Dedicated watcher (optional)

1) Start the watcher:

```bash
python watch_audio_folder.py
```

2) Copy your audio file into `audio_inbox/` (supports `.wav` and `.mp3`).

3) Results will appear in `audio_outbox/` as `<filename>.json`.

Notes:
- `.wav` is recommended.
- `.mp3` requires `ffmpeg` in PATH.
- You must have an offline STT backend installed (e.g., `faster-whisper` / `openai-whisper` / `vosk` + local model).

### Install Whisper (pip) and use it

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Install `ffmpeg` (required for `.mp3`):
- Windows: install ffmpeg and ensure `ffmpeg` is on PATH

Run with pip Whisper backend:

```bash
set SCAM_SHIELD_STT_BACKEND=whisper
python main.py
```

If language auto-detect is wrong, force Hindi/Tamil/Malayalam/Telugu:

```bash
set SCAM_SHIELD_STT_BACKEND=whisper
set SCAM_SHIELD_LANGUAGE=hi
python main.py
```
