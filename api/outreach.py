"""
api/outreach.py — Vercel Serverless Function for Email Outreach

POST /api/outreach
    Body (JSON, optional): { "lead_id": "<firestore_doc_id>", "dry_run": false }
    Header: Authorization: Bearer <SENDGRID_API_KEY>

Returns JSON with send results.
"""

import os
import sys
import json
import logging
import traceback
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = logging.getLogger("api.outreach")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Simple in-process rate-limit store (resets on cold start, good enough for serverless)
_RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", 20))
_rate_window_start: float = 0.0
_rate_count: int = 0


def _check_rate_limit() -> bool:
    """Return True if the request is within the rate limit, False if exceeded."""
    global _rate_window_start, _rate_count
    now = time.time()
    if now - _rate_window_start > 3600:
        _rate_window_start = now
        _rate_count = 0
    if _rate_count >= _RATE_LIMIT_PER_HOUR:
        return False
    _rate_count += 1
    return True


def _authenticate(headers: dict) -> bool:
    """Verify the Bearer token matches the DASHBOARD_AUTH_TOKEN env var."""
    auth_header = headers.get("Authorization") or headers.get("authorization", "")
    expected = os.environ.get("DASHBOARD_AUTH_TOKEN", "")
    if not expected:
        # If no token is configured, block all requests to avoid accidental exposure
        return False
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        return token == expected
    return False


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler — POST triggers outreach for queued leads."""

    def do_POST(self):  # noqa: N802
        started_at = datetime.now(tz=timezone.utc).isoformat()

        # ── Authentication ────────────────────────────────────────────────────
        headers_dict = {k: v for k, v in self.headers.items()}
        if not _authenticate(headers_dict):
            self._respond(401, {"status": "error", "message": "Unauthorized"})
            return

        # ── Rate limiting ─────────────────────────────────────────────────────
        if not _check_rate_limit():
            self._respond(429, {"status": "error", "message": "Rate limit exceeded"})
            return

        # ── Parse request body ────────────────────────────────────────────────
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            body = json.loads(body_bytes or b"{}")
        except json.JSONDecodeError:
            body = {}

        lead_id = body.get("lead_id")
        dry_run = bool(body.get("dry_run", False))

        # ── Run outreach ──────────────────────────────────────────────────────
        try:
            import outreach as outreach_module

            outreach_module.run_outreach(dry_run=dry_run, target_lead_id=lead_id)

            self._respond(200, {
                "status": "ok",
                "message": "Outreach completed" + (" (dry run)" if dry_run else ""),
                "ran_at": started_at,
            })
        except EnvironmentError as exc:
            log.error("Outreach env error: %s", exc)
            self._respond(500, {"status": "error", "message": str(exc)})
        except Exception as exc:
            log.error("Outreach failed: %s\n%s", exc, traceback.format_exc())
            self._respond(500, {"status": "error", "message": str(exc)})

    def do_GET(self):  # noqa: N802
        self._respond(405, {"status": "error", "message": "Method not allowed. Use POST."})

    def _respond(self, status_code: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # noqa: N802
        log.info(fmt, *args)
