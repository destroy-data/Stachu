#!/usr/bin/env python3
"""HTTP server for Piper TTS — used as xiaozhi-server's `custom` TTS backend.

POST /        {"text": "..."} -> audio/wav
GET  /health                  -> {"status": "ok", "model": "<basename>"}

Run under the piper-tts uv tool env:
    uv run --with piper-tts python extra/piper_http.py --model /path/to/voice.onnx
"""

import argparse
import io
import json
import os
import sys
import time
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer

from piper import PiperVoice


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def make_handler(voice: PiperVoice, model_name: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/health":
                self.send_error(404)
                return
            body = json.dumps({"status": "ok", "model": model_name}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            try:
                text = (
                    (json.loads(self.rfile.read(length)) or {}).get("text", "").strip()
                )
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            if not text:
                self.send_error(400, "empty text")
                return

            buf = io.BytesIO()
            t0 = time.monotonic()
            with wave.open(buf, "wb") as wav:
                voice.synthesize_wav(text, wav)
            elapsed_ms = (time.monotonic() - t0) * 1000
            wav_bytes = buf.getvalue()

            print(
                f"POST / synth ms={elapsed_ms:.0f} bytes={len(wav_bytes)} text_len={len(text)}",
                file=sys.stderr,
                flush=True,
            )

            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav_bytes)))
            self.end_headers()
            self.wfile.write(wav_bytes)

        def log_message(self, fmt, *args):
            return

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="Path to Piper .onnx voice model")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=2139)
    args = ap.parse_args()

    model_name = os.path.basename(args.model)
    print(f"loading model={args.model}", file=sys.stderr, flush=True)
    voice = PiperVoice.load(args.model)

    t0 = time.monotonic()
    with wave.open(io.BytesIO(), "wb") as wav:
        voice.synthesize_wav("test", wav)
    print(
        f"warmup ok {(time.monotonic() - t0) * 1000:.0f}ms", file=sys.stderr, flush=True
    )

    handler = make_handler(voice, model_name)
    server = ReusableHTTPServer((args.host, args.port), handler)
    print(f"serving on http://{args.host}:{args.port}", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
