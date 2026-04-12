"""
scheduler.py — Scheduled Execution for Legal Sentinel 2026
Feature 5: Run sentinel.py on a configurable interval using APScheduler.

Usage:
    python scheduler.py                   # Run on the default schedule (every 6 hours)
    python scheduler.py --interval 2      # Run every 2 hours
    python scheduler.py --once            # Run sentinel once and exit

Environment variables:
    SENTINEL_INTERVAL_HOURS — Override interval (default: 6)
    RUN_ANALYTICS_AFTER     — Set to "1" to run analytics.py after each sentinel run
    All variables required by sentinel.py must also be set.
"""

import os
import sys
import time
import logging
import argparse
import signal
import importlib
import runpy
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("scheduler")

# ── Configuration ─────────────────────────────────────────────────────────────
SENTINEL_INTERVAL_HOURS = float(os.environ.get("SENTINEL_INTERVAL_HOURS", 6))
RUN_ANALYTICS_AFTER = os.environ.get("RUN_ANALYTICS_AFTER", "0") == "1"

# Resolve the directory that contains sentinel.py (same dir as this file)
BASE_DIR = Path(__file__).parent.resolve()


# ── Job implementations ───────────────────────────────────────────────────────
def run_sentinel() -> None:
    """Execute sentinel.py as a subprocess-free module run."""
    log.info("=== Sentinel job starting at %s ===",
             datetime.now(tz=timezone.utc).isoformat())
    try:
        # runpy executes the script in a fresh namespace without spawning a new process.
        runpy.run_path(str(BASE_DIR / "sentinel.py"), run_name="__main__")
        log.info("=== Sentinel job completed successfully ===")
    except SystemExit as exc:
        # sentinel.py may call sys.exit; treat exit(0) as success
        if exc.code not in (0, None):
            log.error("sentinel.py exited with code %s", exc.code)
            raise
    except Exception as exc:
        log.error("Sentinel job failed: %s", exc, exc_info=True)
        raise


def run_analytics_snapshot() -> None:
    """Run a quick daily analytics snapshot after the sentinel job."""
    log.info("Running post-sentinel analytics snapshot…")
    try:
        # Import analytics dynamically to avoid top-level env-var validation at import time
        import analytics as analytics_module
        import firebase_admin
        import json
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            key_dict = json.loads(os.environ["FIREBASE_KEY_PATH"])
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)

        db = firestore.client()
        leads = analytics_module.fetch_all_leads(db)
        metrics = analytics_module.compute_metrics(leads)
        analytics_module.store_analytics_snapshot(db, metrics, period="daily")
        log.info("Analytics snapshot stored.")
    except Exception as exc:
        log.warning("Analytics snapshot failed (non-fatal): %s", exc)


def sentinel_job() -> None:
    """The scheduled job: runs sentinel then optionally analytics."""
    run_sentinel()
    if RUN_ANALYTICS_AFTER:
        run_analytics_snapshot()


# ── APScheduler event listener ────────────────────────────────────────────────
def _job_listener(event) -> None:
    if event.exception:
        log.error(
            "Job '%s' raised an exception: %s", event.job_id, event.exception
        )
    else:
        log.info("Job '%s' executed successfully.", event.job_id)


# ── Graceful shutdown ─────────────────────────────────────────────────────────
_scheduler: BlockingScheduler | None = None


def _handle_signal(sig, frame) -> None:
    log.info("Signal %s received — shutting down scheduler gracefully…", sig)
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    sys.exit(0)


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    global _scheduler

    parser = argparse.ArgumentParser(description="Legal Sentinel — Scheduler")
    parser.add_argument(
        "--interval", type=float, default=SENTINEL_INTERVAL_HOURS,
        metavar="HOURS", help="Run interval in hours (default: 6)",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run sentinel once immediately and exit",
    )
    args = parser.parse_args()

    if args.once:
        log.info("--once flag set: running sentinel immediately then exiting.")
        sentinel_job()
        return

    interval_hours = args.interval
    log.info(
        "Scheduler starting — sentinel will run every %.1f hour(s). "
        "Analytics after each run: %s",
        interval_hours, RUN_ANALYTICS_AFTER,
    )

    # Register OS signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    _scheduler = BlockingScheduler(timezone="UTC")
    _scheduler.add_listener(_job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    # Schedule the recurring job
    _scheduler.add_job(
        sentinel_job,
        trigger="interval",
        hours=interval_hours,
        id="sentinel_recurring",
        name="Legal Sentinel Lead Collection",
        # Run the first execution immediately on start-up
        next_run_time=datetime.now(tz=timezone.utc),
        max_instances=1,  # Prevent overlapping runs
        misfire_grace_time=300,  # Allow up to 5 minutes late
    )

    log.info("Scheduler started. Press Ctrl+C to stop.")
    try:
        _scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
