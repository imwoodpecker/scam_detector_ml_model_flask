"""
enhanced_scorer.py

Enhanced scoring with multiple detection methods.
"""

from __future__ import annotations

from simple_advanced_scorer import SimpleAdvancedScorer
from scorer import assess_text

class EnhancedScorer:
    """Enhanced scorer combining multiple methods."""
    
    def __init__(self):
        self.advanced_scorer = SimpleAdvancedScorer()
    
    def analyze_text(self, text: str, language: str = 'en') -> dict:
        """Analyze text with enhanced scoring."""
        # Get original assessment
        original_result = assess_text(text, detected_language=language)
        
        # Get advanced assessment
        advanced_result = self.advanced_scorer.analyze_text(text, language)
        
        # Combine results
        combined_score = int(0.6 * original_result.risk_score + 0.4 * advanced_result['risk_score'])
        
        if combined_score >= 85:
            risk_level = 'CRITICAL'
        elif combined_score >= 70:
            risk_level = 'HIGH'
        elif combined_score >= 40:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'risk_score': combined_score,
            'risk_level': risk_level,
            'original_score': original_result.risk_score,
            'advanced_score': advanced_result['risk_score'],
            'confidence': advanced_result['confidence']
        }

if __name__ == "__main__":
    scorer = EnhancedScorer()
    test_text = "Hello I am calling from your bank. Your account will be blocked if you don't provide the OTP immediately."
    result = scorer.analyze_text(test_text)
    print(result)
