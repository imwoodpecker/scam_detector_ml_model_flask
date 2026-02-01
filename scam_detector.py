"""
scam_detector.py

Simple scam detection interface.
"""

from __future__ import annotations

from audio_risk_pipeline import analyze_audio

def detect_scam(audio_file_path: str) -> dict:
    """Detect scam in audio file."""
    try:
        result = analyze_audio(audio_file_path)
        return {
            'success': True,
            'risk_level': result.get('risk_level', 'UNKNOWN'),
            'risk_score': result.get('risk_score', 0),
            'summary': result.get('summary', ''),
            'details': result
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        result = detect_scam(audio_file)
        print(result)
    else:
        print("Usage: python scam_detector.py <audio_file>")
