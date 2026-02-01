"""
engine.py

Core engine for scam detection processing.
"""

from __future__ import annotations

from audio_risk_pipeline import analyze_audio

def process_audio_file(file_path: str) -> dict:
    """Process a single audio file and return results."""
    try:
        result = analyze_audio(file_path)
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def batch_process_audio_files(file_paths: list[str]) -> list[dict]:
    """Process multiple audio files."""
    results = []
    for file_path in file_paths:
        result = process_audio_file(file_path)
        results.append(result)
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        result = process_audio_file(file_path)
        print(result)
    else:
        print("Usage: python engine.py <audio_file_path>")
