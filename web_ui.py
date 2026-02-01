"""
web_ui.py

Simple web UI for scam detection results.
"""

from __future__ import annotations

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Any

class ScamDetectionHandler(SimpleHTTPRequestHandler):
    """Handle web requests for scam detection results."""
    
    def do_GET(self) -> None:
        if self.path == '/':
            self.path = '/index.html'
        return super().do_GET()
    
    def do_POST(self) -> None:
        if self.path == '/api/results':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Get results from audio_outbox
            results = []
            outbox_dir = 'audio_outbox'
            if os.path.exists(outbox_dir):
                for filename in os.listdir(outbox_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(outbox_dir, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            results.append({
                                'filename': filename,
                                'data': data
                            })
                        except Exception:
                            continue
            
            response = {'results': results}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_error(404)

def main() -> None:
    """Start the web UI server."""
    port = 8080
    server = HTTPServer(('localhost', port), ScamDetectionHandler)
    print(f"Web UI running at http://localhost:{port}")
    server.serve_forever()

if __name__ == '__main__':
    main()
