"""
hud_messages.py

HUD message formatting and display utilities.
"""

from __future__ import annotations

from typing import Dict, List

class HUDMessageFormatter:
    """Format messages for HUD display."""
    
    @staticmethod
    def format_risk_alert(risk_level: str, risk_score: float, filename: str) -> str:
        """Format risk alert message."""
        return f"🚨 {risk_level} RISK ({risk_score:.0f}) detected in {filename}"
    
    @staticmethod
    def format_summary(summary: str, max_length: int = 80) -> str:
        """Format summary message."""
        if len(summary) > max_length:
            return summary[:max_length] + "..."
        return summary
    
    @staticmethod
    def format_file_info(filename: str, risk_level: str, risk_score: float) -> Dict:
        """Format file information."""
        return {
            'filename': filename,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'alert': HUDMessageFormatter.format_risk_alert(risk_level, risk_score, filename)
        }
    
    @staticmethod
    def format_status_message(total_files: int, high_risk_count: int) -> str:
        """Format status message."""
        return f"📊 Processed: {total_files} files | 🚨 High Risk: {high_risk_count}"

if __name__ == "__main__":
    # Test message formatting
    formatter = HUDMessageFormatter()
    print(formatter.format_risk_alert("HIGH", 85.5, "test.mp3"))
    print(formatter.format_summary("This is a test summary message", 30))
    print(formatter.format_status_message(10, 3))
