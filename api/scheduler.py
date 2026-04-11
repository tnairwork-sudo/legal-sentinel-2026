"""
api/scheduler.py — Vercel Serverless Function for Legal Sentinel Scheduler

Triggered by Vercel cron (every 6 hours via vercel.json) or manually via GET.
Executes sentinel.py logic and logs results to Firestore.
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

# Add parent directory to path so sentinel/analytics modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = logging.getLogger("api.scheduler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _init_firebase():
    """Initialise Firebase and return a Firestore client."""
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        key_path = os.environ.get("FIREBASE_KEY_PATH")
        if not key_path:
            raise EnvironmentError("FIREBASE_KEY_PATH environment variable is not set.")
        key_dict = json.loads(key_path)
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    from firebase_admin import firestore as fs
    return fs.client()


def _log_run(db, status: str, detail: str, leads_found: int = 0) -> None:
    """Write a scheduler run record to Firestore."""
    from firebase_admin import firestore as fs
    try:
        db.collection("scheduler_runs").add({
            "status": status,
            "detail": detail,
            "leads_found": leads_found,
            "ran_at": fs.SERVER_TIMESTAMP,
        })
    except Exception as exc:
        log.warning("Could not write scheduler run log: %s", exc)


def _run_sentinel(db) -> dict:
    """Execute the sentinel lead-collection logic and return a result summary."""
    import runpy
    sentinel_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "sentinel.py",
    )
    try:
        runpy.run_path(sentinel_path, run_name="__main__")
        return {"success": True, "message": "Sentinel completed successfully"}
    except SystemExit as exc:
        if exc.code in (0, None):
            return {"success": True, "message": "Sentinel exited cleanly"}
        raise RuntimeError(f"sentinel.py exited with code {exc.code}") from exc


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler — responds to GET (cron or manual trigger)."""

    def do_GET(self):  # noqa: N802
        self._handle()

    def do_POST(self):  # noqa: N802
        self._handle()

    def _handle(self):
        started_at = datetime.now(tz=timezone.utc).isoformat()
        db = None

        try:
            db = _init_firebase()
            result = _run_sentinel(db)
            _log_run(db, "success", result["message"])

            body = json.dumps({
                "status": "ok",
                "message": result["message"],
                "ran_at": started_at,
            }).encode()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        except Exception as exc:
            tb = traceback.format_exc()
            log.error("Scheduler run failed: %s\n%s", exc, tb)

            if db:
                _log_run(db, "error", str(exc)[:500])

            body = json.dumps({
                "status": "error",
                "message": str(exc),
                "ran_at": started_at,
            }).encode()

            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, fmt, *args):  # noqa: N802
        log.info(fmt, *args)
