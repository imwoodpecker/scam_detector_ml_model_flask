"""
audio_preprocess.py

Audio preprocessing module for scam detection pipeline.
Provides noise reduction, normalization, and format conversion for MP3/WAV files.
Fully offline-capable with graceful error handling.
"""

from __future__ import annotations

import os
import tempfile
from typing import Tuple

import numpy as np


def _load_audio_fallback(audio_path: str) -> Tuple[np.ndarray, int]:
    """
    Fallback audio loader using scipy.io.wavfile for WAV files only.
    Returns audio data and sample rate.
    """
    try:
        from scipy.io import wavfile
        sr, audio = wavfile.read(audio_path)
        
        # Convert to float32 and normalize to [-1, 1]
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype == np.int32:
            audio = audio.astype(np.float32) / 2147483648.0
        elif audio.dtype == np.uint8:
            audio = (audio.astype(np.float32) - 128.0) / 128.0
        
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        return audio, sr
    except ImportError:
        raise RuntimeError("scipy not available for WAV fallback. Install scipy or ensure librosa is available.")


def _estimate_snr(audio: np.ndarray, noise_floor_percentile: float = 10) -> float:
    """
    Estimate Signal-to-Noise Ratio in dB.
    Uses percentile-based noise floor estimation for robustness.
    """
    # Estimate noise floor using lower percentile
    noise_floor = np.percentile(np.abs(audio), noise_floor_percentile)
    
    # Estimate signal level using higher percentile
    signal_level = np.percentile(np.abs(audio), 90)
    
    if noise_floor < 1e-10:
        return 60.0  # Cap at 60dB for very clean signals
    
    snr_db = 20 * np.log10(signal_level / noise_floor)
    return float(np.clip(snr_db, -20.0, 60.0))


def _high_pass_filter(audio: np.ndarray, sr: int, cutoff: float = 80.0) -> np.ndarray:
    """
    Apply high-pass filter to remove low-frequency rumble.
    Uses simple IIR filter for CPU efficiency.
    """
    try:
        from scipy import signal
        
        # Design high-pass Butterworth filter
        nyquist = sr / 2
        normal_cutoff = cutoff / nyquist
        b, a = signal.butter(4, normal_cutoff, btype='high', analog=False)
        
        # Apply filter
        filtered = signal.filtfilt(b, a, audio)
        return filtered
    except ImportError:
        # Fallback: simple DC offset removal
        return audio - np.mean(audio)


def _spectral_gating_noise_reduction(audio: np.ndarray, sr: int) -> np.ndarray:
    """
    Simple spectral gating noise reduction.
    Reduces stationary noise while preserving speech characteristics.
    """
    try:
        import noisereduce as nr
        
        # Use a conservative noise reduction approach
        # Stationary noise portion is estimated from the first 0.5 seconds
        noise_sample_len = min(int(0.5 * sr), len(audio))
        noise_sample = audio[:noise_sample_len]
        
        # Apply noise reduction with mild settings
        reduced = nr.reduce_noise(
            y=audio,
            sr=sr,
            stationary=True,
            prop_decrease=0.6,  # Conservative reduction
            time_constant_s=2.0,  # Smooth transitions
        )
        return reduced
    except ImportError:
        # Fallback: return original audio if noisereduce not available
        return audio


def _loudness_normalize(audio: np.ndarray, target_loudness: float = -23.0) -> np.ndarray:
    """
    Normalize audio to target loudness in LUFS.
    Uses RMS-based approximation for CPU efficiency.
    """
    # Calculate current RMS
    current_rms = np.sqrt(np.mean(audio ** 2))
    
    if current_rms < 1e-10:
        return audio  # Silent audio
    
    # Target RMS for -23 LUFS (approximate)
    target_rms = 0.1  # Approximate RMS for -23 LUFS
    
    # Calculate gain
    gain = target_rms / current_rms
    
    # Limit gain to avoid excessive amplification
    gain = np.clip(gain, 0.1, 10.0)
    
    # Apply gain
    normalized = audio * gain
    
    # Soft clipping to prevent distortion
    normalized = np.tanh(normalized * 0.95) / 0.95
    
    return normalized


def _calculate_audio_metrics(audio: np.ndarray, sr: int) -> dict:
    """
    Calculate basic audio quality metrics.
    """
    duration = len(audio) / sr
    
    # Estimate silence percentage (samples below threshold)
    silence_threshold = 0.01
    silent_samples = np.sum(np.abs(audio) < silence_threshold)
    silence_percentage = (silent_samples / len(audio)) * 100
    
    # Estimate SNR
    snr_estimate = _estimate_snr(audio)
    
    return {
        "duration_seconds": float(duration),
        "silence_percentage": float(silence_percentage),
        "snr_estimate_db": float(snr_estimate),
        "sample_rate": int(sr),
    }


def preprocess_audio(input_mp3: str) -> str:
    """
    Preprocess audio file for scam detection pipeline.
    
    Args:
        input_mp3: Path to input MP3/WAV file
        
    Returns:
        Path to cleaned WAV file (temporary)
        
    Raises:
        RuntimeError: If audio cannot be processed
    """
    if not os.path.exists(input_mp3):
        raise RuntimeError(f"Audio file not found: {input_mp3}")
    
    # Determine file type
    is_mp3 = input_mp3.lower().endswith('.mp3')
    is_wav = input_mp3.lower().endswith('.wav')
    
    if not (is_mp3 or is_wav):
        raise RuntimeError(f"Unsupported audio format: {input_mp3}. Only MP3 and WAV are supported.")
    
    try:
        # Load audio
        if is_mp3:
            # For MP3, try librosa first (most reliable)
            try:
                import librosa
                audio, sr = librosa.load(input_mp3, sr=16000, mono=True)
            except ImportError:
                # Fallback: try to convert MP3 to WAV using system tools
                raise RuntimeError("MP3 processing requires librosa. Install librosa or provide WAV input.")
        else:
            # For WAV, try librosa first, then scipy fallback
            try:
                import librosa
                audio, sr = librosa.load(input_mp3, sr=16000, mono=True)
            except ImportError:
                audio, sr = _load_audio_fallback(input_mp3)
                # Resample if needed
                if sr != 16000:
                    try:
                        import scipy.signal
                        audio = scipy.signal.resample(audio, int(len(audio) * 16000 / sr))
                        sr = 16000
                    except ImportError:
                        raise RuntimeError("Audio resampling requires scipy. Install scipy or librosa.")
        
        # Calculate original metrics
        original_metrics = _calculate_audio_metrics(audio, sr)
        
        # Apply preprocessing steps
        # 1. High-pass filter to remove low-frequency rumble
        audio = _high_pass_filter(audio, sr, cutoff=80.0)
        
        # 2. Noise reduction using spectral gating
        audio = _spectral_gating_noise_reduction(audio, sr)
        
        # 3. Loudness normalization
        audio = _loudness_normalize(audio, target_loudness=-23.0)
        
        # Calculate final metrics
        final_metrics = _calculate_audio_metrics(audio, sr)
        
        # Save processed audio to temporary WAV file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
        os.close(temp_fd)
        
        # Save using scipy (fallback) or librosa
        try:
            import scipy.io.wavfile
            # Convert to int16 for WAV output
            audio_int16 = (audio * 32767).astype(np.int16)
            scipy.io.wavfile.write(temp_path, sr, audio_int16)
        except ImportError:
            try:
                import soundfile as sf
                sf.write(temp_path, audio, sr)
            except ImportError:
                raise RuntimeError("Audio saving requires scipy or soundfile. Install one of them.")
        
        # Store metrics in a sidecar file for later use
        metrics_path = temp_path.replace('.wav', '_metrics.json')
        import json
        with open(metrics_path, 'w') as f:
            json.dump({
                "original": original_metrics,
                "processed": final_metrics,
                "preprocessing_applied": ["high_pass_filter", "noise_reduction", "loudness_normalization"]
            }, f, indent=2)
        
        return temp_path
        
    except Exception as e:
        raise RuntimeError(f"Audio preprocessing failed: {str(e)}")


def get_audio_metrics(processed_wav_path: str) -> dict:
    """
    Get audio quality metrics for a processed audio file.
    
    Args:
        processed_wav_path: Path to processed WAV file
        
    Returns:
        Dictionary with audio quality metrics
    """
    metrics_path = processed_wav_path.replace('.wav', '_metrics.json')
    
    if os.path.exists(metrics_path):
        try:
            import json
            with open(metrics_path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    
    # Fallback: calculate metrics directly
    try:
        import librosa
        audio, sr = librosa.load(processed_wav_path, sr=None)
        return _calculate_audio_metrics(audio, sr)
    except Exception:
        return {"error": "Could not calculate audio metrics"}


def cleanup_processed_audio(processed_wav_path: str) -> None:
    """
    Clean up temporary processed audio files.
    
    Args:
        processed_wav_path: Path to processed WAV file
    """
    try:
        if os.path.exists(processed_wav_path):
            os.unlink(processed_wav_path)
        
        metrics_path = processed_wav_path.replace('.wav', '_metrics.json')
        if os.path.exists(metrics_path):
            os.unlink(metrics_path)
    except OSError:
        pass  # Ignore cleanup errors
