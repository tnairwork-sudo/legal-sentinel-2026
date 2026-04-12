"""
outreach.py — Email Outreach Automation for Legal Sentinel 2026
Feature 2: Personalized email campaigns via SendGrid with delivery tracking.

Usage:
    python outreach.py                        # Send to all un-emailed leads
    python outreach.py --lead-id <doc_id>     # Target a single lead
    python outreach.py --dry-run              # Preview emails without sending

Environment variables required:
    SENDGRID_API_KEY   — SendGrid API key
    SENDER_EMAIL       — Verified sender address (e.g. tushar@example.com)
    SENDER_NAME        — Display name for the sender
    FIREBASE_KEY_PATH  — Firebase service-account JSON (same as sentinel.py)

Optional:
    RATE_LIMIT_PER_HOUR  — Max emails per hour (default: 20)
    MAX_RETRIES          — Retry attempts for failed sends (default: 3)
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timezone
from typing import Optional

import requests
import firebase_admin
from firebase_admin import credentials, firestore

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("outreach")

# ── Configuration ─────────────────────────────────────────────────────────────
SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"
RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", 20))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", 3))
RETRY_DELAY_SECONDS = 5  # base delay; doubles on each retry


# ── Firebase initialisation (shared with sentinel.py) ────────────────────────
def _init_firebase() -> firestore.Client:
    if not firebase_admin._apps:
        key_path = os.environ.get("FIREBASE_KEY_PATH")
        if not key_path:
            raise EnvironmentError("FIREBASE_KEY_PATH environment variable is not set.")
        key_dict = json.loads(key_path)
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ── Email Templates ───────────────────────────────────────────────────────────
def build_email_html(lead: dict) -> str:
    """Return a personalised HTML email body for the given lead."""
    name = lead.get("name", "Counsel")
    company = lead.get("company", "your firm")
    draft = lead.get("draft", "").strip()
    service_tag = lead.get("service_tag", "Boutique Advisory")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Georgia', serif; background: #f9f6f0; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 600px; margin: 40px auto; background: #fff; border-radius: 8px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden; }}
    .header {{ background: #050505; padding: 32px 40px; }}
    .header h1 {{ color: #B8860B; font-size: 22px; margin: 0; letter-spacing: 0.08em; }}
    .header p {{ color: #888; font-size: 11px; margin: 4px 0 0; letter-spacing: 0.25em;
                 text-transform: uppercase; }}
    .body {{ padding: 36px 40px; color: #222; line-height: 1.7; font-size: 15px; }}
    .badge {{ display: inline-block; background: #fdf3d0; color: #7a5900; border-radius: 20px;
              padding: 3px 14px; font-size: 11px; font-weight: 700; letter-spacing: 0.15em;
              text-transform: uppercase; margin-bottom: 20px; }}
    .divider {{ border: none; border-top: 1px solid #eee; margin: 28px 0; }}
    .footer {{ background: #f4f4f4; padding: 20px 40px; font-size: 11px; color: #999;
               text-align: center; letter-spacing: 0.05em; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>Tushar Nair, SC</h1>
      <p>Supreme Court Advocate // Strategic Counsel</p>
    </div>
    <div class="body">
      <span class="badge">{service_tag}</span>
      <p>Dear {name},</p>
      <p>{draft}</p>
      <hr class="divider">
      <p style="font-size:13px; color:#555;">
        I would welcome a brief call to explore how we might support {company} on any pending
        regulatory, contractual, or advisory matters.
      </p>
      <p style="font-size:13px; color:#555;">
        Warm regards,<br>
        <strong>Tushar Nair</strong><br>
        Supreme Court Advocate<br>
        <a href="mailto:tushar@tnnair.com" style="color:#B8860B;">tushar@tnnair.com</a>
      </p>
    </div>
    <div class="footer">
      You are receiving this because your firm was identified as a potential fit for our practice.
      To unsubscribe, reply with "Remove" in the subject line.
    </div>
  </div>
</body>
</html>"""


def build_email_text(lead: dict) -> str:
    """Return plain-text fallback for the email."""
    name = lead.get("name", "Counsel")
    company = lead.get("company", "your firm")
    draft = lead.get("draft", "").strip()
    return (
        f"Dear {name},\n\n{draft}\n\n"
        f"I would welcome a brief call regarding {company}.\n\n"
        "Warm regards,\nTushar Nair, Supreme Court Advocate\ntushar@tnnair.com"
    )


# ── SendGrid Delivery ─────────────────────────────────────────────────────────
def _send_via_sendgrid(
    api_key: str,
    sender_email: str,
    sender_name: str,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> dict:
    """
    POST to SendGrid mail/send endpoint.
    Returns a dict with keys: success (bool), status_code (int), message (str).
    """
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": sender_email, "name": sender_name},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(SENDGRID_API_URL, json=payload, headers=headers, timeout=15)

    if resp.status_code in (200, 202):
        return {"success": True, "status_code": resp.status_code, "message": "Sent"}
    return {
        "success": False,
        "status_code": resp.status_code,
        "message": resp.text[:200],
    }


def send_email_with_retry(
    api_key: str,
    sender_email: str,
    sender_name: str,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> dict:
    """Wrap _send_via_sendgrid with exponential-backoff retries."""
    delay = RETRY_DELAY_SECONDS
    for attempt in range(1, MAX_RETRIES + 1):
        result = _send_via_sendgrid(
            api_key, sender_email, sender_name,
            to_email, subject, html_body, text_body,
        )
        if result["success"]:
            return result
        log.warning(
            "Attempt %d/%d failed (HTTP %d): %s — retrying in %ds",
            attempt, MAX_RETRIES, result["status_code"], result["message"], delay,
        )
        if attempt < MAX_RETRIES:
            time.sleep(delay)
            delay *= 2  # exponential back-off
    return result


# ── Firestore helpers ─────────────────────────────────────────────────────────
def _update_email_status(db: firestore.Client, doc_id: str, status: str, detail: str = "") -> None:
    """Write email delivery metadata back to the lead document."""
    db.collection("sentinel_leads").document(doc_id).update({
        "email_status": status,
        "email_detail": detail,
        "last_contacted": firestore.SERVER_TIMESTAMP,
    })


# ── Main outreach loop ────────────────────────────────────────────────────────
def run_outreach(dry_run: bool = False, target_lead_id: Optional[str] = None) -> None:
    """
    Fetch un-emailed leads from Firestore and send personalised outreach.
    Respects RATE_LIMIT_PER_HOUR to avoid spam flags.
    """
    # Validate required env vars
    required = ["SENDGRID_API_KEY", "SENDER_EMAIL", "FIREBASE_KEY_PATH"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    api_key = os.environ["SENDGRID_API_KEY"]
    sender_email = os.environ["SENDER_EMAIL"]
    sender_name = os.environ.get("SENDER_NAME", "Tushar Nair SC")

    db = _init_firebase()

    # Build query
    if target_lead_id:
        docs = [db.collection("sentinel_leads").document(target_lead_id).get()]
        docs = [d for d in docs if d.exists]
        log.info("Targeting single lead: %s", target_lead_id)
    else:
        # Only fetch leads that haven't been emailed yet
        query = (
            db.collection("sentinel_leads")
            .where("email_status", "not-in", ["sent", "skipped"])
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
        )
        try:
            docs = list(query.stream())
        except Exception:
            # Fallback: fetch all and filter locally (index may not exist yet)
            all_docs = db.collection("sentinel_leads").stream()
            docs = [
                d for d in all_docs
                if d.to_dict().get("email_status") not in ("sent", "skipped")
            ]

    if not docs:
        log.info("No leads awaiting outreach.")
        return

    log.info("%d lead(s) queued for outreach.", len(docs))
    interval = 3600 / RATE_LIMIT_PER_HOUR  # seconds between sends

    sent_count = 0
    for doc in docs:
        lead = doc.to_dict()
        doc_id = doc.id
        name = lead.get("name", "Unknown")
        to_email = lead.get("email")

        if not to_email:
            log.warning("No email address for lead '%s' (%s) — skipping.", name, doc_id)
            if not dry_run:
                _update_email_status(db, doc_id, "skipped", "No email address on file")
            continue

        subject = f"A brief note from Tushar Nair SC — {lead.get('company', '')}"
        html_body = build_email_html(lead)
        text_body = build_email_text(lead)

        if dry_run:
            log.info("[DRY-RUN] Would send to %s (%s)", name, to_email)
            log.debug("Subject: %s\n%s", subject, text_body[:200])
            continue

        log.info("Sending outreach to %s (%s)…", name, to_email)
        result = send_email_with_retry(
            api_key, sender_email, sender_name,
            to_email, subject, html_body, text_body,
        )

        if result["success"]:
            _update_email_status(db, doc_id, "sent", "Delivered via SendGrid")
            log.info("✓ Sent to %s", to_email)
            sent_count += 1
        else:
            _update_email_status(
                db, doc_id, "failed",
                f"HTTP {result['status_code']}: {result['message']}",
            )
            log.error("✗ Failed for %s: %s", to_email, result["message"])

        # Rate-limit pause
        time.sleep(interval)

    log.info("Outreach complete. Sent: %d / %d", sent_count, len(docs))


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Legal Sentinel — Email Outreach")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    parser.add_argument("--lead-id", metavar="DOC_ID", help="Target a single Firestore doc")
    args = parser.parse_args()

    run_outreach(dry_run=args.dry_run, target_lead_id=args.lead_id)
