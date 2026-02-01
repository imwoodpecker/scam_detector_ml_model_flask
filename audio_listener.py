"""
audio_listener.py

Audio file listener for real-time processing.
"""

from __future__ import annotations

import os
import time
from typing import Callable

class AudioFileListener:
    """Listen for new audio files in a directory."""
    
    def __init__(self, watch_dir: str = "audio_inbox"):
        self.watch_dir = watch_dir
        self.processed_files = set()
        self.running = False
    
    def start_listening(self, callback: Callable[[str], None]) -> None:
        """Start listening for new audio files."""
        self.running = True
        print(f"Listening for audio files in: {self.watch_dir}")
        
        while self.running:
            try:
                if os.path.exists(self.watch_dir):
                    for filename in os.listdir(self.watch_dir):
                        if self._is_audio_file(filename):
                            filepath = os.path.join(self.watch_dir, filename)
                            if filepath not in self.processed_files:
                                print(f"New audio file detected: {filename}")
                                callback(filepath)
                                self.processed_files.add(filepath)
                
                time.sleep(1)  # Check every second
                
            except KeyboardInterrupt:
                print("\nStopping audio listener...")
                self.running = False
                break
    
    def _is_audio_file(self, filename: str) -> bool:
        """Check if file is an audio file."""
        return filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac'))

if __name__ == "__main__":
    def test_callback(filepath: str):
        print(f"Processing: {filepath}")
    
    listener = AudioFileListener()
    listener.start_listening(test_callback)
