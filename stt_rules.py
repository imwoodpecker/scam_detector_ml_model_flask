"""
stt_rules.py

Speech-to-text processing rules and configurations.
"""

from __future__ import annotations

from typing import Dict, List

class STTRules:
    """Speech-to-text processing rules."""
    
    @staticmethod
    def get_language_hints() -> Dict[str, List[str]]:
        """Get language hints for better STT accuracy."""
        return {
            'hi': ['hindi', 'bharat', 'india'],
            'ta': ['tamil', 'chennai', 'madras'],
            'te': ['telugu', 'hyderabad', 'andhra'],
            'ml': ['malayalam', 'kerala', 'malabar'],
            'en': ['english', 'usa', 'uk', 'australia']
        }
    
    @staticmethod
    def get_noise_patterns() -> List[str]:
        """Get common noise patterns to filter."""
        return [
            'uh', 'um', 'ah', 'er', 'hmm',
            '...', '----', '====',
            '[noise]', '[silence]', '[background]'
        ]
    
    @staticmethod
    def clean_transcript(text: str) -> str:
        """Clean transcript text."""
        # Remove noise patterns
        for pattern in STTRules.get_noise_patterns():
            text = text.replace(pattern, '')
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text.strip()

if __name__ == "__main__":
    rules = STTRules()
    print("Language hints:", rules.get_language_hints())
    print("Noise patterns:", rules.get_noise_patterns())
    print("Cleaned text:", rules.clean_transcript("Hello... uh... this is a test [noise]"))
