"""
simple_advanced_scorer.py

Simplified but powerful scam detection with advanced patterns.
"""

import re
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class ScamPattern:
    """Simple scam pattern with scoring."""
    keywords: List[str]
    weight: int
    category: str

class SimpleAdvancedScorer:
    """Simplified advanced scam detector."""
    
    def __init__(self):
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> List[ScamPattern]:
        """Load comprehensive scam patterns."""
        return [
            # High-risk financial patterns
            ScamPattern(['otp', 'one time password', 'verification code', 'security code'], 25, 'FINANCIAL'),
            ScamPattern(['account will be blocked', 'account suspended', 'account frozen'], 30, 'FINANCIAL'),
            ScamPattern(['transfer money', 'send payment', 'wire funds', 'immediately'], 35, 'FINANCIAL'),
            
            # Authority impersonation
            ScamPattern(['calling from bank', 'calling from paypal', 'calling from amazon', 'calling from microsoft'], 20, 'AUTHORITY'),
            ScamPattern(['fraud department', 'security team', 'verification center'], 25, 'AUTHORITY'),
            ScamPattern(['federal bureau', 'fbi', 'cia', 'irs', 'police'], 30, 'AUTHORITY'),
            
            # Urgency tactics
            ScamPattern(['immediately', 'right now', 'urgent', 'asap', 'without delay'], 15, 'URGENCY'),
            ScamPattern(['legal action', 'arrest warrant', 'court case', 'lawsuit'], 25, 'URGENCY'),
            
            # Payment methods
            ScamPattern(['gift card', 'itunes card', 'amazon card', 'google play card'], 30, 'PAYMENT'),
            ScamPattern(['bitcoin', 'crypto', 'cryptocurrency', 'western union', 'money gram'], 25, 'PAYMENT'),
            
            # Hindi patterns
            ScamPattern(['ओटीपी', 'otp बताइए', 'otp bataye', 'otp dijiye'], 30, 'FINANCIAL'),
            ScamPattern(['अकाउंट ब्लॉक', 'account block', 'बैंक से बोल रहा'], 35, 'AUTHORITY'),
            ScamPattern(['तुरंत', 'अभी', 'immediately', 'urgent'], 20, 'URGENCY'),
            
            # Tamil patterns
            ScamPattern(['ஓடிபி', 'otp sollungal', 'otp kodungal'], 30, 'FINANCIAL'),
            ScamPattern(['கணக்கு தடுக்கப்படும்', 'account blocked'], 35, 'FINANCIAL'),
            
            # Telugu patterns
            ScamPattern(['ఓటిపి', 'otp cheppandi', 'otp cheptundi'], 30, 'FINANCIAL'),
            ScamPattern(['ఖాతా బ్లాక్', 'account block'], 35, 'FINANCIAL'),
            
            # Malayalam patterns
            ScamPattern(['ഒടിപി', 'otp parayu', 'otp nalku'], 30, 'FINANCIAL'),
            ScamPattern(['അക്കൗണ്ട് ബ്ലോക്ക്', 'account block'], 35, 'FINANCIAL'),
        ]
    
    def analyze_text(self, text: str, language: str = 'en') -> Dict:
        """Analyze text for scam patterns."""
        
        # Normalize text
        text = text.lower().strip()
        
        # Find matching patterns
        matches = []
        total_score = 0
        
        for pattern in self.patterns:
            for keyword in pattern.keywords:
                if keyword in text:
                    matches.append({
                        'keyword': keyword,
                        'category': pattern.category,
                        'weight': pattern.weight
                    })
                    total_score += pattern.weight
        
        # Calculate contextual factors
        urgency_count = len([w for w in ['urgent', 'immediate', 'now', 'asap', 'hurry'] if w in text])
        financial_count = len([w for w in ['money', 'payment', 'transfer', 'account', 'bank', 'card'] if w in text])
        authority_count = len([w for w in ['bank', 'police', 'fbi', 'court', 'legal', 'official'] if w in text])
        
        # Apply multipliers
        multiplier = 1.0
        if urgency_count > 0:
            multiplier += 0.2 * urgency_count
        if financial_count > 2:
            multiplier += 0.3
        if authority_count > 0:
            multiplier += 0.2
        
        final_score = min(100, total_score * multiplier)
        
        # Determine risk level
        if final_score >= 80:
            risk_level = 'CRITICAL'
        elif final_score >= 60:
            risk_level = 'HIGH'
        elif final_score >= 30:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        # Calculate confidence
        confidence = min(1.0, len(matches) / 5.0)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(risk_level, matches)
        
        return {
            'risk_score': final_score,
            'risk_level': risk_level,
            'matches': matches,
            'confidence': confidence,
            'context_analysis': {
                'urgency_count': urgency_count,
                'financial_count': financial_count,
                'authority_count': authority_count,
                'multiplier': multiplier
            },
            'recommendations': recommendations
        }
    
    def _generate_recommendations(self, risk_level: str, matches: List[Dict]) -> List[str]:
        """Generate recommendations based on risk level."""
        recommendations = []
        
        if risk_level in ['HIGH', 'CRITICAL']:
            recommendations.append("IMMEDIATE ACTION: This appears to be a scam call")
            recommendations.append("Do not provide any personal or financial information")
            recommendations.append("Hang up immediately and verify through official channels")
        
        categories = set(m['category'] for m in matches)
        if 'FINANCIAL' in categories:
            recommendations.append("FINANCIAL WARNING: Never share OTPs or banking details")
        if 'AUTHORITY' in categories:
            recommendations.append("AUTHORITY WARNING: Verify caller identity independently")
        if 'URGENCY' in categories:
            recommendations.append("URGENCY WARNING: Scammers create false urgency")
        
        return recommendations

def test_simple_advanced():
    """Test the simple advanced scorer."""
    scorer = SimpleAdvancedScorer()
    
    test_cases = [
        ("Hello I am calling from Microsoft. Your account will be blocked if you don't provide the OTP immediately.", "en"),
        ("Hi how are you doing today? Let's schedule a meeting for next week.", "en"),
        ("बैंक से बोल रहा हूं, आपका अकाउंट ब्लॉक हो जाएगा, ओटीपी बताइए तुरंत", "hi"),
        ("Congratulations! You have won a lottery. Send $500 via Western Union to claim your prize.", "en")
    ]
    
    for text, lang in test_cases:
        print(f"\nAnalyzing: {text[:50]}...")
        result = scorer.analyze_text(text, lang)
        print(f"Risk Level: {result['risk_level']} ({result['risk_score']:.1f})")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Matches: {len(result['matches'])}")
        if result['recommendations']:
            print("Top recommendation:", result['recommendations'][0])

if __name__ == "__main__":
    test_simple_advanced()
