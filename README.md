# legal-sentinel-2026

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/tnairwork-sudo/legal-sentinel-2026&env=GEMINI_API_KEY,APOLLO_API_KEY,FIREBASE_KEY_PATH,SENDGRID_API_KEY,DASHBOARD_AUTH_TOKEN)

AI-powered legal lead intelligence and outreach automation for Tushar Nair SC.

## One-Click Vercel Deployment

1. Click the **Deploy with Vercel** button above.
2. Vercel will prompt you for the required environment variables:
   - `GEMINI_API_KEY` — Google AI Studio API key
   - `APOLLO_API_KEY` — Apollo.io API key
   - `FIREBASE_KEY_PATH` — Firebase service-account JSON (paste the full JSON string)
   - `SENDGRID_API_KEY` — SendGrid API key
   - `DASHBOARD_AUTH_TOKEN` — Any strong secret string you choose (used to authenticate dashboard → API calls)
3. Click **Deploy**. Vercel builds and deploys everything automatically.
4. The scheduler cron runs every 6 hours to collect new leads.
5. Access the dashboard at `https://<your-project>.vercel.app`.
6. On first visit, enter your `DASHBOARD_AUTH_TOKEN` in the token field at the bottom of the page to enable the Outreach action button.

### Optional Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SCHEDULER_INTERVAL` | `6` | Hours between automatic sentinel runs |
| `RATE_LIMIT_PER_HOUR` | `20` | Maximum outreach emails sent per hour |
| `SENDER_EMAIL` | *(required for outreach)* | Verified SendGrid sender address |
| `SENDER_NAME` | `Tushar Nair SC` | Display name for outreach emails |

## Features

- 📊 Real-time lead pipeline dashboard (Firestore-backed)
- 🤖 AI-generated outreach drafts via Gemini 1.5 Flash
- 📧 Personalised email campaigns via SendGrid
- 📈 Analytics: contact rates, conversion rates, MRR tracking
- ⏰ Automated lead collection every 6 hours (Vercel cron)
- 🔍 Search, filter, and status pipeline management

## Local Development

```bash
pip install -r requirements.txt

# Copy and fill in your keys
cp .env.example .env

# Run once
python sentinel.py

# Start the scheduler (every 6 hours)
python scheduler.py
```