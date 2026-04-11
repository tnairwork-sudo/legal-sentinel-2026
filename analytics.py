"""
analytics.py — Lead Analytics & Reporting for Legal Sentinel 2026
Feature 3: Track metrics, generate reports, store analytics in Firestore.

Usage:
    python analytics.py                     # Compute & store today's snapshot
    python analytics.py --report weekly     # Print a weekly summary
    python analytics.py --report monthly    # Print a monthly summary
    python analytics.py --export csv        # Export leads to leads_export.csv

Environment variables required:
    FIREBASE_KEY_PATH  — Firebase service-account JSON (same as sentinel.py)
"""

import os
import sys
import csv
import json
import logging
import argparse
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("analytics")

# ── Constants ─────────────────────────────────────────────────────────────────
MRR_TARGET = 45_000          # $ monthly recurring revenue target
AVG_DEAL_VALUE = 5_000       # $ average retainer value per conversion


# ── Firebase init ─────────────────────────────────────────────────────────────
def _init_firebase() -> firestore.Client:
    if not firebase_admin._apps:
        key_path = os.environ.get("FIREBASE_KEY_PATH")
        if not key_path:
            raise EnvironmentError("FIREBASE_KEY_PATH environment variable is not set.")
        key_dict = json.loads(key_path)
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ── Data helpers ──────────────────────────────────────────────────────────────
def _ts_to_dt(ts) -> datetime | None:
    """Convert a Firestore Timestamp or None → datetime (UTC)."""
    if ts is None:
        return None
    if hasattr(ts, "seconds"):
        return datetime.fromtimestamp(ts.seconds, tz=timezone.utc)
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return None


def fetch_all_leads(db: firestore.Client) -> list[dict]:
    """Return every document in sentinel_leads as a list of dicts with doc_id."""
    docs = db.collection("sentinel_leads").stream()
    leads = []
    for doc in docs:
        d = doc.to_dict()
        d["_id"] = doc.id
        leads.append(d)
    return leads


# ── Core metrics calculation ──────────────────────────────────────────────────
def compute_metrics(leads: list[dict], since: datetime | None = None) -> dict[str, Any]:
    """
    Calculate lead pipeline metrics.

    Args:
        leads: list of lead dicts (from Firestore)
        since: optional datetime; when set, only leads collected on/after this
               date are counted in totals (still uses full list for status counts)
    Returns:
        dict with keys: total, contacted, converted, rejected, new,
                        contact_rate_pct, conversion_rate_pct,
                        revenue_actual, revenue_projection,
                        sources, statuses
    """
    if since:
        scoped = [
            l for l in leads
            if _ts_to_dt(l.get("timestamp")) and _ts_to_dt(l.get("timestamp")) >= since
        ]
    else:
        scoped = leads

    total = len(scoped)
    statuses: dict[str, int] = defaultdict(int)
    sources: dict[str, int] = defaultdict(int)

    for lead in scoped:
        status = lead.get("status", "new").lower()
        statuses[status] += 1
        tag = lead.get("service_tag", "Unknown")
        sources[tag] += 1

    contacted = statuses.get("contacted", 0) + statuses.get("qualified", 0) \
                + statuses.get("proposal_sent", 0) + statuses.get("converted", 0)
    converted = statuses.get("converted", 0)
    rejected = statuses.get("rejected", 0)
    new = statuses.get("new", 0)

    conversion_value_total = sum(
        lead.get("conversion_value", AVG_DEAL_VALUE)
        for lead in scoped
        if lead.get("status") == "converted"
    )

    contact_rate = round((contacted / total * 100), 1) if total > 0 else 0.0
    conversion_rate = round((converted / total * 100), 1) if total > 0 else 0.0
    revenue_projection = round(converted * AVG_DEAL_VALUE, 2)

    return {
        "total": total,
        "new": new,
        "contacted": contacted,
        "converted": converted,
        "rejected": rejected,
        "contact_rate_pct": contact_rate,
        "conversion_rate_pct": conversion_rate,
        "revenue_actual": conversion_value_total,
        "revenue_projection": revenue_projection,
        "mrr_target": MRR_TARGET,
        "mrr_progress_pct": round(revenue_projection / MRR_TARGET * 100, 1),
        "sources": dict(sources),
        "statuses": dict(statuses),
    }


# ── Firestore snapshot storage ─────────────────────────────────────────────────
def store_analytics_snapshot(db: firestore.Client, metrics: dict, period: str = "daily") -> str:
    """
    Write a metrics snapshot to Firestore analytics collection.
    Returns the new document ID.
    """
    payload = {
        **metrics,
        "period": period,
        "computed_at": firestore.SERVER_TIMESTAMP,
    }
    _, ref = db.collection("analytics").add(payload)
    log.info("Analytics snapshot stored: %s (period=%s)", ref.id, period)
    return ref.id


# ── Report generation ─────────────────────────────────────────────────────────
def _print_report(metrics: dict, period: str, since: datetime | None) -> None:
    since_str = since.strftime("%Y-%m-%d") if since else "all time"
    print(f"\n{'='*60}")
    print(f"  LEGAL SENTINEL — {period.upper()} ANALYTICS REPORT")
    print(f"  Period: {since_str} → now")
    print(f"{'='*60}")
    print(f"  Total Leads Collected : {metrics['total']}")
    print(f"  New (un-contacted)    : {metrics['new']}")
    print(f"  Contacted             : {metrics['contacted']}")
    print(f"  Converted             : {metrics['converted']}")
    print(f"  Rejected              : {metrics['rejected']}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Contact Rate          : {metrics['contact_rate_pct']}%")
    print(f"  Conversion Rate       : {metrics['conversion_rate_pct']}%")
    print(f"  Revenue (actual)      : ${metrics['revenue_actual']:,.0f}")
    print(f"  Revenue (projected)   : ${metrics['revenue_projection']:,.0f}")
    print(f"  MRR Target Progress   : {metrics['mrr_progress_pct']}% of ${metrics['mrr_target']:,}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Lead Sources:")
    for src, cnt in sorted(metrics["sources"].items(), key=lambda x: -x[1]):
        print(f"    {src:<30} {cnt}")
    print(f"  Status Breakdown:")
    for st, cnt in sorted(metrics["statuses"].items(), key=lambda x: -x[1]):
        print(f"    {st:<30} {cnt}")
    print(f"{'='*60}\n")


# ── CSV export ────────────────────────────────────────────────────────────────
def export_to_csv(leads: list[dict], filename: str = "leads_export.csv") -> None:
    """Export all leads to a CSV file."""
    if not leads:
        log.warning("No leads to export.")
        return

    fieldnames = [
        "_id", "name", "company", "service_tag", "email",
        "status", "pipeline_stage", "notes",
        "email_status", "last_contacted", "conversion_value",
        "timestamp", "draft",
    ]

    def _fmt(val) -> str:
        if val is None:
            return ""
        dt = _ts_to_dt(val)
        if dt:
            return dt.strftime("%Y-%m-%d %H:%M UTC")
        return str(val)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            row = {k: _fmt(lead.get(k)) if k in ("timestamp", "last_contacted") else lead.get(k, "")
                   for k in fieldnames}
            writer.writerow(row)

    log.info("Exported %d leads → %s", len(leads), filename)
    print(f"CSV exported: {filename}  ({len(leads)} rows)")


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Legal Sentinel — Analytics & Reporting")
    parser.add_argument(
        "--report", choices=["daily", "weekly", "monthly"],
        default="daily", help="Report period (default: daily)",
    )
    parser.add_argument(
        "--export", choices=["csv"], help="Export leads data",
    )
    parser.add_argument(
        "--no-store", action="store_true",
        help="Compute metrics but do not write to Firestore",
    )
    args = parser.parse_args()

    db = _init_firebase()
    leads = fetch_all_leads(db)
    log.info("Fetched %d total leads from Firestore.", len(leads))

    # Determine the reporting window
    now = datetime.now(tz=timezone.utc)
    period_map = {
        "daily": now - timedelta(days=1),
        "weekly": now - timedelta(weeks=1),
        "monthly": now - timedelta(days=30),
    }
    since = period_map[args.report]

    metrics = compute_metrics(leads, since=since)
    _print_report(metrics, args.report, since)

    if not args.no_store:
        store_analytics_snapshot(db, metrics, period=args.report)

    if args.export == "csv":
        export_to_csv(leads)


if __name__ == "__main__":
    main()
