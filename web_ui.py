"""
web_ui.py

Minimal local web UI for the streaming scam engine.

- Uses ONLY Python standard library (no external deps).
- Serves a small HTML/JS page on http://127.0.0.1:8000/
- Accepts text chunks via fetch() and returns live risk snapshots.

Intended usage:
- PC: run `python web_ui.py` and open the URL in a browser.
- Android: run the same script in Termux, then open the URL in mobile browser.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

from scorer import StreamingScorer
from stt_rules import assess_stt_quality


class SessionState:
    """
    Simple in-memory session for a single browser tab.
    Not multi-tenant; the goal is a basic, offline UI.
    """

    def __init__(self) -> None:
        self.scorer = StreamingScorer(session_id="web")
        self.closed = False

    def ingest(self, text: str) -> dict:
        q = assess_stt_quality(text)
        snap = self.scorer.ingest_chunk(text)
        result = {
            "chunk_index": snap.chunk_index,
            "risk_score": snap.risk_score,
            "risk_level": snap.risk_level,
            "new_signals": snap.newly_detected_signals,
            "stt_tier": q.tier,
            "stt_reasons": q.reasons,
        }
        return result

    def finalize(self) -> dict:
        self.closed = True
        final = self.scorer.finalize()
        return {
            "risk_score": final.risk_score,
            "risk_level": final.risk_level,
            "signals": final.signals,
            "trace": [
                {
                    "chunk": t.chunk_index,
                    "rule": t.rule_id,
                    "change": t.change,
                    "why": t.why,
                }
                for t in final.trace
            ],
        }


class Handler(BaseHTTPRequestHandler):
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _session: ClassVar[SessionState | None] = None

    def _get_session(self) -> SessionState:
        with self._lock:
            if self._session is None or self._session.closed:
                self._session = SessionState()
            return self._session

    def _send_json(self, obj: dict, status: int = 200) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # type: ignore[override]
        if self.path == "/" or self.path.startswith("/index"):
            self._send_html(INDEX_HTML)
        else:
            self.send_error(404, "Not found")

    def do_POST(self) -> None:  # type: ignore[override]
        if self.path != "/chunk":
            self.send_error(404, "Not found")
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self._send_json({"error": "invalid_json"}, status=400)
            return

        text = str(payload.get("text", "") or "")
        end_session = bool(payload.get("end", False))

        s = self._get_session()
        if end_session:
            result = s.finalize()
            self._send_json({"final": result})
            return

        if not text.strip():
            self._send_json({"error": "empty_chunk"})
            return

        snapshot = s.ingest(text)
        self._send_json({"snapshot": snapshot})


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Scam Shield Live UI</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #05070a;
      color: #e4e7ec;
      margin: 0;
      padding: 16px;
    }
    .shell {
      max-width: 800px;
      margin: 0 auto;
    }
    h1 {
      font-size: 20px;
      margin-bottom: 4px;
    }
    .subtitle {
      font-size: 13px;
      color: #9da4b5;
      margin-bottom: 16px;
    }
    textarea {
      width: 100%;
      min-height: 90px;
      border-radius: 8px;
      border: 1px solid #222634;
      background: #0b0f19;
      color: inherit;
      padding: 8px 10px;
      resize: vertical;
    }
    button {
      border-radius: 999px;
      border: none;
      padding: 8px 18px;
      font-size: 13px;
      cursor: pointer;
      margin-right: 8px;
      margin-top: 8px;
    }
    .primary {
      background: #2563eb;
      color: white;
    }
    .secondary {
      background: #111827;
      color: #e4e7ec;
      border: 1px solid #374151;
    }
    .row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
    }
    .pill {
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .pill-minimal { background: #111827; color: #9ca3af; }
    .pill-low { background: #0f172a; color: #4ade80; }
    .pill-medium { background: #1f2933; color: #facc15; }
    .pill-high { background: #2b1b1b; color: #f97373; }
    pre {
      background: #050814;
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 11px;
      overflow-x: auto;
      border: 1px solid #111827;
      max-height: 260px;
    }
    .panel {
      margin-top: 16px;
      border-radius: 10px;
      padding: 10px 12px;
      background: #050814;
      border: 1px solid #111827;
    }
    .label {
      font-size: 12px;
      color: #9da4b5;
      margin-bottom: 4px;
    }
  </style>
</head>
<body>
  <div class="shell">
    <h1>Scam Shield – Live Engine</h1>
    <div class="subtitle">
      Runs fully offline. Type or paste what the caller says in short chunks (1–3 seconds each).
    </div>

    <div>
      <div class="label">Current chunk</div>
      <textarea id="chunk" placeholder="Example: URGENT, your account may be blocked. Share the OTP you received."></textarea>
      <div class="row">
        <button class="primary" id="sendBtn">Send chunk</button>
        <button class="secondary" id="endBtn">End session</button>
        <span id="status" style="font-size:12px;color:#9da4b5;"></span>
      </div>
    </div>

    <div class="panel">
      <div class="label">Live risk</div>
      <div class="row">
        <span id="riskPill" class="pill pill-minimal">MINIMAL</span>
        <span id="riskScore" style="font-size:12px;color:#9da4b5;">score: 0/100</span>
      </div>
      <div id="signals" style="font-size:12px;color:#9da4b5;margin-top:4px;"></div>
    </div>

    <div class="panel">
      <div class="label">Session log (snapshots & final report)</div>
      <pre id="log"></pre>
    </div>
  </div>

  <script>
    const chunkEl = document.getElementById('chunk');
    const sendBtn = document.getElementById('sendBtn');
    const endBtn = document.getElementById('endBtn');
    const statusEl = document.getElementById('status');
    const riskPill = document.getElementById('riskPill');
    const riskScore = document.getElementById('riskScore');
    const signalsEl = document.getElementById('signals');
    const logEl = document.getElementById('log');

    function setRisk(level, score) {
      riskPill.className = 'pill pill-' + (level || 'minimal');
      riskPill.textContent = (level || 'minimal').toUpperCase();
      riskScore.textContent = 'score: ' + (score || 0) + '/100';
    }

    function appendLog(line) {
      logEl.textContent += line + '\\n';
      logEl.scrollTop = logEl.scrollHeight;
    }

    async function postChunk(payload) {
      const res = await fetch('/chunk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      return res.json();
    }

    sendBtn.onclick = async () => {
      const text = chunkEl.value.trim();
      chunkEl.value = '';
      if (!text) {
        statusEl.textContent = 'Enter some text first.';
        return;
      }
      statusEl.textContent = 'Sending...';
      try {
        const data = await postChunk({ text });
        if (data.error) {
          statusEl.textContent = 'Error: ' + data.error;
          return;
        }
        const s = data.snapshot;
        setRisk(s.risk_level, s.risk_score);
        const sigs = (s.new_signals || []).join(', ') || 'none';
        signalsEl.textContent = 'new signals: ' + sigs + ' · STT: ' + s.stt_tier;
        appendLog('- chunk ' + s.chunk_index + ': score=' + s.risk_score + ' level=' + s.risk_level + ' signals=' + sigs);
        statusEl.textContent = 'Chunk processed.';
      } catch (e) {
        statusEl.textContent = 'Network error (still offline, but request failed).';
      }
    };

    endBtn.onclick = async () => {
      statusEl.textContent = 'Ending session...';
      try {
        const data = await postChunk({ end: true });
        const f = data.final;
        appendLog('--- final_report ---');
        appendLog('risk_score: ' + f.risk_score + '/100');
        appendLog('risk_level: ' + f.risk_level);
        appendLog('signals: ' + (f.signals || []).join(', '));
        appendLog('trace:');
        (f.trace || []).forEach(t => {
          appendLog('  - chunk ' + t.chunk + ': ' + t.rule + ' ' + (t.change >= 0 ? '+' : '') + t.change + ' (' + t.why + ')');
        });
        statusEl.textContent = 'Session ended. You can start a new one by sending another chunk.';
      } catch (e) {
        statusEl.textContent = 'Failed to end session.';
      }
    };

    setRisk('minimal', 0);
  </script>
</body>
</html>
"""


def main() -> int:
    server = HTTPServer(("127.0.0.1", 8000), Handler)
    print("Scam Shield web UI running at http://127.0.0.1:8000/ (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

