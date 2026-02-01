"""
stt/transcriber.py

Offline-capable audio-file speech-to-text with timestamps.

Supported inputs:
- .wav (recommended, easiest fully-offline)
- .mp3 (requires ffmpeg installed OR an installed decoder library)

Backends (auto-detected):
- Whisper (local): `whisper` (OpenAI Whisper) or `faster_whisper`
- Vosk (local): `vosk` + a local model directory

No network calls are made by this module. If the selected backend needs model
files, they must exist locally; otherwise we raise a clear error.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from typing import Literal, TypedDict


class Segment(TypedDict):
    start: float
    end: float
    text: str


class TranscriptionMeta(TypedDict, total=False):
    backend: str
    language: str | None
    language_probability: float | None


BackendName = Literal["whisper", "faster_whisper", "vosk"]


@dataclass(frozen=True)
class TranscriberConfig:
    backend: BackendName | None = None
    # For whisper/faster-whisper: model name or local path (must exist if path-like)
    model: str = "tiny"
    # For Vosk: local model directory (must exist)
    vosk_model_path: str | None = None
    language: str | None = None  # e.g. "en", "hi"
    # faster-whisper performance knobs (CPU defaults to int8 for speed)
    device: str = "cpu"
    compute_type: str | None = "int8"
    # faster-whisper decoding knobs (balanced for speed/accuracy)
    beam_size: int = 2
    best_of: int = 2
    # Use VAD to skip silence (often big speedup for call recordings)
    vad_filter: bool = True
    # Optional: only transcribe first N seconds (fast "quick scan")
    max_audio_seconds: float | None = None


def _is_path_like(s: str) -> bool:
    return os.path.sep in s or (os.path.altsep and os.path.altsep in s) or s.endswith((".bin", ".pt", ".onnx"))


def _ensure_wav_pcm16_mono_16k(audio_path: str) -> str:
    """
    Ensure we have a WAV file suitable for Vosk (pcm16 mono 16k).
    If input is wav but not in expected format, we still convert.
    Uses ffmpeg if available.
    """

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        # If already a wav, try to proceed without conversion.
        if audio_path.lower().endswith(".wav"):
            return audio_path
        raise RuntimeError("MP3 decoding requires ffmpeg in PATH (offline) or a wav input file.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()
    out_path = tmp.name

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        audio_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        out_path,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        try:
            os.unlink(out_path)
        except OSError:
            pass
        raise RuntimeError(f"ffmpeg failed to decode/convert audio: {p.stderr.strip() or p.stdout.strip()}")
    return out_path


def _extract_audio_clip(audio_path: str, *, seconds: float) -> str:
    """
    Create a temporary clipped audio file containing only the first `seconds`.
    Uses ffmpeg if available; otherwise returns original audio_path.
    """

    if seconds <= 0:
        return audio_path
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return audio_path

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_path)[1] or ".wav")
    tmp.close()
    out_path = tmp.name

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        audio_path,
        "-t",
        str(float(seconds)),
        out_path,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        try:
            os.unlink(out_path)
        except OSError:
            pass
        return audio_path
    return out_path


class AudioTranscriber:
    def __init__(self, config: TranscriberConfig | None = None) -> None:
        self.config = config or TranscriberConfig()

    def transcribe(self, audio_path: str) -> list[Segment]:
        backend = self.config.backend or self._auto_backend()
        if backend == "faster_whisper":
            return self._transcribe_faster_whisper(audio_path)
        if backend == "whisper":
            return self._transcribe_whisper(audio_path)
        if backend == "vosk":
            return self._transcribe_vosk(audio_path)
        raise RuntimeError(f"Unsupported backend: {backend}")

    def _auto_backend(self) -> BackendName:
        # Prefer faster-whisper if available, then whisper, then vosk.
        try:
            import faster_whisper  # noqa: F401

            return "faster_whisper"
        except Exception:
            pass
        try:
            import whisper  # noqa: F401

            return "whisper"
        except Exception:
            pass
        try:
            import vosk  # noqa: F401

            return "vosk"
        except Exception:
            pass
        raise RuntimeError("No STT backend available. Install one of: faster-whisper, whisper, or vosk (offline).")

    def _transcribe_whisper(self, audio_path: str) -> list[Segment]:
        import whisper

        model_name = self.config.model
        if _is_path_like(model_name) and not os.path.exists(model_name):
            raise RuntimeError(f"Whisper model path does not exist: {model_name}")

        m = whisper.load_model(model_name)
        result = m.transcribe(audio_path, language=self.config.language, fp16=False)
        segs: list[Segment] = []
        for s in result.get("segments", []):
            text = (s.get("text") or "").strip()
            if not text:
                continue
            segs.append({"start": float(s["start"]), "end": float(s["end"]), "text": text})
        return segs

    def _transcribe_faster_whisper(self, audio_path: str) -> list[Segment]:
        from faster_whisper import WhisperModel

        # Explicitly use CPU and default to the "tiny" model if not overridden.
        model_name = self.config.model or "tiny"
        if _is_path_like(model_name) and not os.path.exists(model_name):
            raise RuntimeError(f"faster-whisper model path does not exist: {model_name}")

        path = audio_path
        cleanup = False
        if self.config.max_audio_seconds is not None:
            clipped = _extract_audio_clip(audio_path, seconds=float(self.config.max_audio_seconds))
            if clipped != audio_path:
                path = clipped
                cleanup = True
        try:
            m = WhisperModel(model_name, device=self.config.device, compute_type=self.config.compute_type)
            segments, _info = m.transcribe(
                path,
                language=self.config.language,
                vad_filter=bool(self.config.vad_filter),
                beam_size=int(self.config.beam_size),
                best_of=int(self.config.best_of),
            )
        finally:
            if cleanup:
                try:
                    os.unlink(path)
                except OSError:
                    pass
        out: list[Segment] = []
        for s in segments:
            text = (s.text or "").strip()
            if not text:
                continue
            out.append({"start": float(s.start), "end": float(s.end), "text": text})
        return out

    def _transcribe_vosk(self, audio_path: str) -> list[Segment]:
        import json

        from vosk import KaldiRecognizer, Model

        model_path = self.config.vosk_model_path or os.environ.get("VOSK_MODEL_PATH")
        if not model_path:
            raise RuntimeError("Vosk backend selected but no model path provided. Set VOSK_MODEL_PATH or config.vosk_model_path.")
        if not os.path.isdir(model_path):
            raise RuntimeError(f"Vosk model directory not found: {model_path}")

        wav_path = _ensure_wav_pcm16_mono_16k(audio_path)
        cleanup = wav_path != audio_path

        try:
            with wave.open(wav_path, "rb") as wf:
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
                    # If conversion didn't happen (no ffmpeg) and wav is incompatible, fail clearly.
                    raise RuntimeError("Vosk requires 16kHz mono PCM16 WAV. Provide such a wav or install ffmpeg.")

                rec = KaldiRecognizer(Model(model_path), wf.getframerate())
                rec.SetWords(True)

                segs: list[Segment] = []
                # We build segments from final results; Vosk provides word times.
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    rec.AcceptWaveform(data)

                final = json.loads(rec.FinalResult() or "{}")
                words = final.get("result") or []
                if not words:
                    return []

                # Group words into ~3s segments deterministically.
                cur_words: list[str] = []
                seg_start = float(words[0]["start"])
                seg_end = float(words[0]["end"])
                for w in words:
                    ws = float(w["start"])
                    we = float(w["end"])
                    if we - seg_start > 3.0 and cur_words:
                        segs.append({"start": seg_start, "end": seg_end, "text": " ".join(cur_words).strip()})
                        cur_words = []
                        seg_start = ws
                        seg_end = we
                    cur_words.append(str(w["word"]))
                    seg_end = we
                if cur_words:
                    segs.append({"start": seg_start, "end": seg_end, "text": " ".join(cur_words).strip()})
                return segs
        finally:
            if cleanup:
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass


def transcribe_file(audio_path: str, config: TranscriberConfig | None = None) -> list[Segment]:
    """
    Convenience function matching the spec.
    """

    return AudioTranscriber(config).transcribe(audio_path)


def transcribe_file_with_meta(audio_path: str, config: TranscriberConfig | None = None) -> tuple[list[Segment], TranscriptionMeta]:
    """
    Transcribe and also return best-effort metadata like detected language.

    Notes:
    - faster-whisper can auto-detect language when config.language is None
    - whisper returns a top-level "language" in its result dict
    - vosk does not provide reliable language detection here
    """

    cfg = config or TranscriberConfig()
    backend = cfg.backend or AudioTranscriber(cfg)._auto_backend()

    if backend == "faster_whisper":
        from faster_whisper import WhisperModel

        model_name = cfg.model or "tiny"
        if _is_path_like(model_name) and not os.path.exists(model_name):
            raise RuntimeError(f"faster-whisper model path does not exist: {model_name}")

        path = audio_path
        cleanup = False
        if cfg.max_audio_seconds is not None:
            clipped = _extract_audio_clip(audio_path, seconds=float(cfg.max_audio_seconds))
            if clipped != audio_path:
                path = clipped
                cleanup = True

        try:
            m = WhisperModel(model_name, device=cfg.device, compute_type=cfg.compute_type)
            # Pass 1: auto-detect language if not specified.
            seg_iter, info = m.transcribe(
                path,
                language=cfg.language,
                vad_filter=bool(cfg.vad_filter),
                beam_size=int(cfg.beam_size),
                best_of=int(cfg.best_of),
            )
            detected_lang = getattr(info, "language", None)

            # If Hindi/Tamil/Malayalam/Telugu is detected, force that language in a second pass.
            force_langs = {"hi", "ta", "ml", "te"}
            if cfg.language is None and isinstance(detected_lang, str) and detected_lang in force_langs:
                seg_iter, info = m.transcribe(
                    path,
                    language=detected_lang,
                    vad_filter=bool(cfg.vad_filter),
                    beam_size=int(cfg.beam_size),
                    best_of=int(cfg.best_of),
                )
                detected_lang = getattr(info, "language", detected_lang)

            segs: list[Segment] = []
            for s in seg_iter:
                text = (s.text or "").strip()
                if not text:
                    continue
                segs.append({"start": float(s.start), "end": float(s.end), "text": text})
        finally:
            if cleanup:
                try:
                    os.unlink(path)
                except OSError:
                    pass

        meta: TranscriptionMeta = {
            "backend": "faster_whisper",
            "language": detected_lang,
            "language_probability": float(getattr(info, "language_probability", 0.0) or 0.0) if getattr(info, "language_probability", None) is not None else None,
        }
        return segs, meta

    if backend == "whisper":
        import whisper

        model_name = cfg.model
        if _is_path_like(model_name) and not os.path.exists(model_name):
            raise RuntimeError(f"Whisper model path does not exist: {model_name}")

        m = whisper.load_model(model_name)
        result = m.transcribe(audio_path, language=cfg.language, fp16=False)
        segs: list[Segment] = []
        for s in result.get("segments", []):
            text = (s.get("text") or "").strip()
            if not text:
                continue
            segs.append({"start": float(s["start"]), "end": float(s["end"]), "text": text})

        meta = {
            "backend": "whisper",
            "language": result.get("language"),
            "language_probability": None,
        }
        return segs, meta

    # vosk (or unknown): fall back to existing behavior, but no language info
    segs = AudioTranscriber(cfg).transcribe(audio_path)
    return segs, {"backend": backend, "language": None, "language_probability": None}

