"""
api/analytics.py — Vercel Serverless Function for Analytics Data

GET /api/analytics
    Returns JSON with lead pipeline metrics for dashboard charts.
    Results are cached for 5 minutes to avoid excessive Firestore reads.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = logging.getLogger("api.analytics")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Simple in-process cache ────────────────────────────────────────────────────
_CACHE_TTL_SECONDS = 300  # 5 minutes
_cache: dict = {"data": None, "expires_at": 0.0}


def _get_cached_metrics() -> dict | None:
    if _cache["data"] and time.time() < _cache["expires_at"]:
        return _cache["data"]
    return None


def _set_cache(metrics: dict) -> None:
    _cache["data"] = metrics
    _cache["expires_at"] = time.time() + _CACHE_TTL_SECONDS


def _init_firebase():
    import firebase_admin
    from firebase_admin import credentials

    if not firebase_admin._apps:
        key_path = os.environ.get("FIREBASE_KEY_PATH")
        if not key_path:
            raise EnvironmentError("FIREBASE_KEY_PATH environment variable is not set.")
        key_dict = json.loads(key_path)
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    from firebase_admin import firestore
    return firestore.client()


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler — GET returns pipeline analytics as JSON."""

    def do_GET(self):  # noqa: N802
        fetched_at = datetime.now(tz=timezone.utc).isoformat()

        # ── Check cache ───────────────────────────────────────────────────────
        cached = _get_cached_metrics()
        if cached:
            self._respond(200, {**cached, "cached": True, "fetched_at": fetched_at})
            return

        # ── Fetch from Firestore and compute metrics ───────────────────────────
        try:
            import analytics as analytics_module

            db = _init_firebase()
            leads = analytics_module.fetch_all_leads(db)
            metrics = analytics_module.compute_metrics(leads)

            _set_cache(metrics)

            self._respond(200, {
                **metrics,
                "cached": False,
                "fetched_at": fetched_at,
                "lead_count": len(leads),
            })

        except EnvironmentError as exc:
            log.error("Analytics env error: %s", exc)
            self._respond(500, {"status": "error", "message": str(exc)})
        except Exception as exc:
            log.error("Analytics fetch failed: %s", exc)
            self._respond(500, {"status": "error", "message": str(exc)})

    def do_POST(self):  # noqa: N802
        self._respond(405, {"status": "error", "message": "Method not allowed. Use GET."})

    def _respond(self, status_code: int, data: dict) -> None:
        body = json.dumps(data, default=str).encode()
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", f"public, max-age={_CACHE_TTL_SECONDS}")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # noqa: N802
        log.info(fmt, *args)
