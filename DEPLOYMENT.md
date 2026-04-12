# Legal Sentinel 2026 — Deployment Guide

Deploy Legal Sentinel 2026 to your preferred platform.

---

## Table of Contents

1. [Vercel Deployment](#vercel-deployment)
2. [GitHub Actions (Automated Scheduling)](#github-actions-automated-scheduling)
3. [AWS Lambda Deployment](#aws-lambda-deployment)
4. [Docker Self-Hosting](#docker-self-hosting)

---

## Vercel Deployment

Vercel runs the dashboard and triggers the sentinel on a cron schedule.

### Prerequisites

- A [Vercel account](https://vercel.com/signup) (free tier works)
- Your repository pushed to GitHub

### Step 1: Import the Project

1. Go to [https://vercel.com/new](https://vercel.com/new)
2. Click **"Import Git Repository"**
3. Select `tnairwork-sudo/legal-sentinel-2026`
4. Click **"Import"**

### Step 2: Configure Environment Variables

In the Vercel project settings, add each of the following as environment variables:

| Variable | Where to Get It |
|----------|----------------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikeys) |
| `APOLLO_API_KEY` | [Apollo.io Settings](https://app.apollo.io/settings/integrations/api) |
| `FIREBASE_KEY_PATH` | Firebase Console → Project Settings → Service Accounts |
| `SENDGRID_API_KEY` | [SendGrid API Keys](https://app.sendgrid.com/settings/api_keys) |
| `SENDER_EMAIL` | Your verified SendGrid sender address |
| `SENDER_NAME` | Your display name (e.g., `Tushar Nair SC`) |

**Steps:**
1. Go to your project on Vercel → **Settings** → **Environment Variables**
2. Add each variable above for the **Production** environment
3. Click **Save**

### Step 3: Deploy

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy from the project root
vercel --prod
```

Or push to your `main` branch — Vercel auto-deploys on every push.

### Step 4: Verify the Cron Job

The `vercel.json` file configures a cron job to call `/api/run-sentinel` every 6 hours.

1. Go to your project on Vercel → **Crons** tab
2. Confirm the cron job is listed and active
3. Click **"Run Now"** to test it manually

> **Note:** Vercel Cron Jobs require a **Pro plan** or higher. On the free Hobby plan,
> use [GitHub Actions](#github-actions-automated-scheduling) for scheduling instead.

---

## GitHub Actions (Automated Scheduling)

GitHub Actions provides free scheduled execution with 2,000 minutes/month on free accounts.

### Step 1: Add GitHub Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"** for each of the following:

| Secret Name | Value |
|-------------|-------|
| `GEMINI_API_KEY` | Your Gemini AI API key |
| `APOLLO_API_KEY` | Your Apollo.io API key |
| `FIREBASE_KEY_PATH` | Your Firebase service account JSON (single line) |
| `SENDGRID_API_KEY` | Your SendGrid API key |
| `SENDER_EMAIL` | Your verified sender email |
| `SENDER_NAME` | Your sender display name |

### Step 2: Enable the Workflow

The workflow file at `.github/workflows/daily_run.yml` is already configured to:

- Run automatically every 6 hours
- Accept manual triggers from the GitHub Actions UI
- Log all execution results
- Send failure notifications via GitHub's built-in alerting

**Verify the workflow is active:**

1. Go to your repository → **Actions** tab
2. Find **"Legal Sentinel — Scheduled Lead Collection"**
3. Click **"Enable workflow"** if it shows as disabled

### Step 3: Test a Manual Run

1. Go to **Actions** → **"Legal Sentinel — Scheduled Lead Collection"**
2. Click **"Run workflow"** → **"Run workflow"**
3. Watch the logs to confirm everything runs correctly

### Failure Notifications

GitHub Actions automatically emails you when a workflow fails. To configure:

1. Go to **Settings** → **Notifications**
2. Ensure **"Actions"** → **"Failed workflows"** is enabled for your account

---

## AWS Lambda Deployment

Deploy to AWS Lambda for serverless execution with pay-per-use pricing.

### Prerequisites

- AWS account with appropriate IAM permissions
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed
- Python 3.12

### Step 1: Package the Application

```bash
# Create deployment package
mkdir lambda_package
pip install -r requirements.txt -t lambda_package/
cp sentinel.py outreach.py analytics.py scheduler.py lambda_package/

# Create ZIP archive
cd lambda_package
zip -r ../legal-sentinel-lambda.zip .
cd ..
```

### Step 2: Create the Lambda Function

```bash
# Create the function
aws lambda create-function \
  --function-name legal-sentinel \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler sentinel.lambda_handler \
  --zip-file fileb://legal-sentinel-lambda.zip \
  --timeout 300 \
  --memory-size 256
```

### Step 3: Set Environment Variables

```bash
aws lambda update-function-configuration \
  --function-name legal-sentinel \
  --environment Variables="{
    GEMINI_API_KEY=your_key,
    APOLLO_API_KEY=your_key,
    FIREBASE_KEY_PATH='{...json...}',
    SENDGRID_API_KEY=your_key,
    SENDER_EMAIL=your@email.com,
    SENDER_NAME='Tushar Nair SC'
  }"
```

### Step 4: Schedule with EventBridge

```bash
# Create a rule to trigger every 6 hours
aws events put-rule \
  --name legal-sentinel-schedule \
  --schedule-expression "rate(6 hours)" \
  --state ENABLED

# Add Lambda as the target
aws events put-targets \
  --rule legal-sentinel-schedule \
  --targets "Id=legal-sentinel,Arn=arn:aws:lambda:REGION:ACCOUNT_ID:function:legal-sentinel"
```

### Step 5: Grant EventBridge Permission

```bash
aws lambda add-permission \
  --function-name legal-sentinel \
  --statement-id allow-eventbridge \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:REGION:ACCOUNT_ID:rule/legal-sentinel-schedule
```

> **Cost estimate:** ~$0.00 for typical usage (free tier covers 1M requests/month).

---

## Docker Self-Hosting

Run Legal Sentinel on any server or cloud VM with Docker.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- A Linux server (Ubuntu 22.04+ recommended)

### Step 1: Create Dockerfile

Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run the scheduler
CMD ["python", "scheduler.py"]
```

### Step 2: Build the Image

```bash
docker build -t legal-sentinel .
```

### Step 3: Create Your Environment File

```bash
cp .env.example .env
# Edit .env with your actual API keys
nano .env
```

### Step 4: Run the Container

```bash
# Run the scheduler continuously (restarts automatically on failure)
docker run -d \
  --name legal-sentinel \
  --env-file .env \
  --restart unless-stopped \
  legal-sentinel

# View logs
docker logs -f legal-sentinel
```

### Step 5: Update the Container

```bash
# Pull latest code
git pull

# Rebuild and restart
docker build -t legal-sentinel .
docker stop legal-sentinel
docker rm legal-sentinel
docker run -d \
  --name legal-sentinel \
  --env-file .env \
  --restart unless-stopped \
  legal-sentinel
```

### Docker Compose (Optional)

Create `docker-compose.yml`:

```yaml
version: "3.9"
services:
  sentinel:
    build: .
    env_file: .env
    restart: unless-stopped
    command: python scheduler.py
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Run with:
```bash
docker compose up -d
docker compose logs -f
```

---

## Security Best Practices

- **Never commit `.env` files** to version control
- Use your platform's native secret management (Vercel env vars, GitHub Secrets, AWS Secrets Manager)
- Rotate API keys every 90 days and immediately if compromised
- Use least-privilege IAM roles for AWS deployments
- Enable Firebase Security Rules to restrict database access
- Monitor SendGrid activity logs for unusual sending patterns
- Set up billing alerts on all paid services to avoid unexpected charges
