# Legal Sentinel 2026 — Setup Guide

Get the system running locally in under 15 minutes.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [API Key Acquisition](#api-key-acquisition)
   - [Gemini AI (Google)](#1-gemini-ai-google)
   - [Apollo.io](#2-apolloio)
   - [Firebase](#3-firebase)
   - [SendGrid](#4-sendgrid)
3. [Local Development Setup](#local-development-setup)
4. [Testing the System](#testing-the-system)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/tnairwork-sudo/legal-sentinel-2026.git
cd legal-sentinel-2026

# 2. Create your environment file
cp .env.example .env

# 3. Fill in your API keys (see API Key Acquisition below)
nano .env      # or use any text editor

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Run the sentinel
python sentinel.py
```

---

## API Key Acquisition

You need keys from **four** services. All have free tiers sufficient for personal use.

---

### 1. Gemini AI (Google)

**Used by:** `sentinel.py` — AI-powered lead analysis and strategy drafting.

| Step | Action |
|------|--------|
| 1 | Go to [https://aistudio.google.com/app/apikeys](https://aistudio.google.com/app/apikeys) |
| 2 | Sign in with your Google account |
| 3 | Click **"Create API Key"** |
| 4 | Select your Google Cloud project (or create a new one) |
| 5 | Copy the generated key |

Set in `.env`:
```
GEMINI_API_KEY=AIza...your_key_here
```

> **Free tier:** Gemini Flash is free with generous rate limits. No billing required.

---

### 2. Apollo.io

**Used by:** `sentinel.py` — Lead discovery database.

| Step | Action |
|------|--------|
| 1 | Create a free account at [https://www.apollo.io/](https://www.apollo.io/) |
| 2 | Go to [https://app.apollo.io/settings/integrations/api](https://app.apollo.io/settings/integrations/api) |
| 3 | Click **"API Keys"** in the left sidebar |
| 4 | Click **"Create New Key"** |
| 5 | Give it a name (e.g., `legal-sentinel`) and copy the key |

Set in `.env`:
```
APOLLO_API_KEY=your_apollo_key_here
```

> **Free tier:** Apollo's free plan includes 50 export credits/month. Paid plans provide more.

---

### 3. Firebase

**Used by:** `sentinel.py`, `outreach.py`, `analytics.py` — Lead database storage.

#### 3a. Create a Firebase Project

| Step | Action |
|------|--------|
| 1 | Go to [https://console.firebase.google.com/](https://console.firebase.google.com/) |
| 2 | Click **"Add project"** |
| 3 | Name it `tnlaw-87ba6` (or any name you prefer) |
| 4 | Disable Google Analytics if not needed → **Create project** |

#### 3b. Enable Firestore

| Step | Action |
|------|--------|
| 1 | In your project, click **"Firestore Database"** in the left sidebar |
| 2 | Click **"Create database"** |
| 3 | Select **"Production mode"** → Choose a region → **Enable** |

#### 3c. Download Service Account Key

| Step | Action |
|------|--------|
| 1 | Click the ⚙️ gear icon → **"Project settings"** |
| 2 | Click the **"Service accounts"** tab |
| 3 | Click **"Generate new private key"** → **"Generate key"** |
| 4 | A JSON file will download to your computer |

#### 3d. Format the Key for `.env`

The entire JSON must be on **one line** with no line breaks:

```bash
# On macOS/Linux — convert the downloaded JSON to a single line:
cat firebase-key.json | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)))"
```

Set in `.env`:
```
FIREBASE_KEY_PATH={"type":"service_account","project_id":"tnlaw-87ba6",...entire JSON on one line...}
```

> **Free tier:** Firebase Spark plan is free. Includes 1 GB Firestore storage and 50K reads/day.

---

### 4. SendGrid

**Used by:** `outreach.py` — Email campaign delivery.

| Step | Action |
|------|--------|
| 1 | Create a free account at [https://sendgrid.com/](https://sendgrid.com/) |
| 2 | Go to [https://app.sendgrid.com/settings/api_keys](https://app.sendgrid.com/settings/api_keys) |
| 3 | Click **"Create API Key"** |
| 4 | Choose **"Restricted Access"** → enable **"Mail Send"** → **"Create & View"** |
| 5 | Copy the key (you won't see it again) |

#### Verify Your Sender Email

Before sending emails, verify your sender address:

| Step | Action |
|------|--------|
| 1 | Go to [https://app.sendgrid.com/settings/sender_auth](https://app.sendgrid.com/settings/sender_auth) |
| 2 | Click **"Verify a Single Sender"** |
| 3 | Fill in your details and click **"Create"** |
| 4 | Check your email and click the verification link |

Set in `.env`:
```
SENDGRID_API_KEY=SG.your_key_here
SENDER_EMAIL=your_verified_email@example.com
SENDER_NAME=Tushar Nair SC
```

> **Free tier:** SendGrid free plan includes 100 emails/day forever.

---

## Local Development Setup

### Prerequisites

- Python 3.10 or later
- `pip` package manager
- Git

### Step-by-Step

```bash
# 1. Clone and enter the repo
git clone https://github.com/tnairwork-sudo/legal-sentinel-2026.git
cd legal-sentinel-2026

# 2. (Optional) Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your environment file
cp .env.local.example .env
# Edit .env with your actual API keys

# 5. Load environment variables (python-dotenv handles this automatically)
#    Or export manually:
export $(grep -v '^#' .env | xargs)
```

---

## Testing the System

### Verify Environment Variables

```bash
python3 -c "
import os
required = ['GEMINI_API_KEY', 'APOLLO_API_KEY', 'FIREBASE_KEY_PATH', 'SENDGRID_API_KEY']
missing = [v for v in required if not os.environ.get(v)]
if missing:
    print('Missing:', missing)
else:
    print('All required variables are set ✓')
"
```

### Run Each Component

```bash
# Test lead collection (sentinel)
python sentinel.py

# Test email outreach (dry run — no emails sent)
python outreach.py --dry-run

# Test analytics report
python analytics.py --report daily --no-store

# Test the scheduler (runs once and exits)
python scheduler.py --once
```

### Run the Scheduler Continuously

```bash
# Run with default 6-hour interval
python scheduler.py

# Run every 2 hours
python scheduler.py --interval 2

# Run sentinel once then exit
python scheduler.py --once
```

---

## Troubleshooting

### `Missing required environment variables`

**Cause:** Your `.env` file is missing or variables are not exported.

**Fix:**
```bash
# Make sure .env exists
ls -la .env

# Load variables into your shell
export $(grep -v '^#' .env | xargs)

# Or use python-dotenv (automatically loaded by scripts using load_dotenv())
pip install python-dotenv
```

---

### `Apollo API Error 422`

**Cause:** Invalid search parameters sent to Apollo.

**Fix:** Check your `APOLLO_API_KEY` is correct and your account has active credits.

---

### `Firebase: Invalid service account`

**Cause:** The `FIREBASE_KEY_PATH` JSON is malformed or has line breaks.

**Fix:** Ensure the entire JSON is on a single line with no embedded newlines:
```bash
# Reformat your firebase key file
python3 -c "import json; d=json.load(open('firebase-key.json')); print(json.dumps(d))"
```
Copy the output into your `.env` file.

---

### `SendGrid 403 Forbidden`

**Cause:** Your sender email is not verified with SendGrid.

**Fix:** Complete Single Sender Verification at:
[https://app.sendgrid.com/settings/sender_auth](https://app.sendgrid.com/settings/sender_auth)

---

### `ModuleNotFoundError`

**Cause:** Python dependencies not installed.

**Fix:**
```bash
pip install -r requirements.txt
```

---

### Gemini API quota exceeded

**Cause:** You've hit the free-tier rate limit.

**Fix:** Wait a minute and retry, or upgrade your Google AI Studio plan. The free tier resets hourly.

---

## Security Best Practices

- **Never commit your `.env` file** — it is listed in `.gitignore` by default.
- Use `.env.example` to share the variable _names_ without real values.
- Rotate API keys periodically and immediately if leaked.
- Use environment-specific keys: different keys for development vs production.
- For production, use your platform's secret management (Vercel env vars, GitHub Secrets, AWS Secrets Manager) instead of `.env` files.
