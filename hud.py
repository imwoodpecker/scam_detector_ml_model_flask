"""
hud.py

Heads-up display for scam detection monitoring.
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, List

class ScamHUD:
    """Heads-up display for scam detection monitoring."""
    
    def __init__(self):
        self.last_results = []
        self.running = True
    
    def monitor_outbox(self, outbox_dir: str = "audio_outbox") -> None:
        """Monitor the outbox directory for new results."""
        print("Scam Detection HUD - Monitoring Results")
        print("=" * 50)
        
        while self.running:
            try:
                if os.path.exists(outbox_dir):
                    results = self._load_results(outbox_dir)
                    self._display_results(results)
                
                time.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                print("\nStopping HUD...")
                self.running = False
                break
    
    def _load_results(self, outbox_dir: str) -> List[Dict]:
        """Load results from outbox directory."""
        results = []
        for filename in os.listdir(outbox_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(outbox_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    results.append({
                        'filename': filename,
                        'risk_level': data.get('risk_level', 'UNKNOWN'),
                        'risk_score': data.get('risk_score', 0),
                        'summary': data.get('summary', '')
                    })
                except Exception:
                    continue
        return results
    
    def _display_results(self, results: List[Dict]) -> None:
        """Display results in HUD format."""
        if results != self.last_results:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("Scam Detection HUD")
            print("=" * 50)
            print(f"Total Files Processed: {len(results)}")
            print()
            
            for result in results:
                risk_color = self._get_risk_color(result['risk_level'])
                print(f"File: {result['filename'][:30]}...")
                print(f"Risk: {risk_color}{result['risk_level']} ({result['risk_score']})\033[0m")
                print(f"Summary: {result['summary'][:60]}...")
                print("-" * 50)
            
            self.last_results = results
    
    def _get_risk_color(self, risk_level: str) -> str:
        """Get color code for risk level."""
        colors = {
            'LOW': '\033[92m',      # Green
            'MEDIUM': '\033[93m',   # Yellow
            'HIGH': '\033[91m',     # Red
            'CRITICAL': '\033[95m', # Magenta
            'UNKNOWN': '\033[94m'   # Blue
        }
        return colors.get(risk_level, '\033[0m')

if __name__ == "__main__":
    hud = ScamHUD()
    hud.monitor_outbox()
