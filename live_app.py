"""
live_app.py

Live application for real-time scam detection.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from scorer import StreamingScorer

def main() -> None:
    """Run live scam detection application."""
    parser = argparse.ArgumentParser(description="Live scam detection from stdin")
    parser.add_argument("--session", default="default", help="Session ID")
    args = parser.parse_args()
    
    scorer = StreamingScorer(session_id=args.session)
    
    print("Live scam detection started. Type text and press Enter.")
    print("Type 'quit' to exit.")
    
    try:
        while True:
            try:
                text = input("> ")
                if text.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not text.strip():
                    continue
                
                snapshot = scorer.ingest_chunk(text)
                result = asdict(snapshot)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                
            except KeyboardInterrupt:
                break
            except EOFError:
                break
    
    finally:
        final = scorer.finalize()
        print("\nFinal assessment:")
        print(json.dumps(asdict(final), ensure_ascii=False, indent=2))

def run() -> None:
    """Run live application."""
    main()

if __name__ == '__main__':
    main()
