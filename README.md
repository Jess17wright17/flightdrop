# FlightDrop — Setup Guide

A flight price alert service. Users sign up on your landing page,
you poll Amadeus for prices, and email them when fares drop.

---

## Files in this project

| File | What it does |
|------|-------------|
| `index.html` | Landing page — users sign up here |
| `app.py` | Flask web server — saves subscribers to database |
| `checker.py` | Price checker — runs on a schedule, sends alert emails |
| `requirements.txt` | Python packages list |
| `.env.example` | Template for your secret API keys |

---

## Step 1 — Get your API keys (free)

### Amadeus (flight data)
1. Go to https://developers.amadeus.com
2. Click "Get started for free" and create an account
3. Create a new app — you'll get a **Client ID** and **Client Secret**
4. Note: the free "test" environment has sample data. For real prices,
   you'll need to request production access (also free, takes 1–2 days)

### Resend (sending emails)
1. Go to https://resend.com and sign up
2. Add and verify your domain (or use their sandbox for testing)
3. Create an API key under "API Keys"

---

## Step 2 — Set up your environment

```bash
# 1. Clone or download this project folder

# 2. Install Python packages
pip install -r requirements.txt

# 3. Copy the env template and fill in your keys
cp .env.example .env
# Then open .env in a text editor and paste your API keys
```

---

## Step 3 — Run the backend server

```bash
python app.py
```

You should see:
```
✅ Database ready.
🚀 FlightDrop server running at http://localhost:5000
```

---

## Step 4 — Open the landing page

Open `index.html` directly in your browser (double-click it).
Fill out the form — you should see "You're in!" and a new row in the database.

To view subscribers: http://localhost:5000/subscribers

---

## Step 5 — Run the price checker

```bash
python checker.py
```

This will check prices for all subscribers and send emails if any drop
below their target price.

---

## Step 6 — Automate the price checker

### Option A — Run it in a loop (simplest)
In `checker.py`, comment out `run_check()` at the bottom and
uncomment the `while True` loop to check every 4 hours.

### Option B — Use a cron job (Mac/Linux)
Run `crontab -e` and add this line to check every 4 hours:
```
0 */4 * * * cd /path/to/flightdrop && python checker.py
```

---

## Step 7 — Deploy online (so it runs 24/7)

### Easiest option: Railway.app
1. Go to https://railway.app and sign up with GitHub
2. Push this folder to a GitHub repo
3. In Railway, click "New Project" → "Deploy from GitHub repo"
4. Add your environment variables under "Variables"
5. Railway will give you a live URL — update it in `index.html`

### Other options
- **Render.com** — similar to Railway, also has a free tier
- **Fly.io** — more control, still beginner-friendly
- **DigitalOcean** — $4/mo, most reliable for production

---

## Monetization next steps

1. **Add Stripe** — use `stripe` Python package to charge $7/mo for
   tracking more than 1 route (freemium model)

2. **Add affiliate links** — replace the Google Flights link in alert
   emails with a Skyscanner or Kayak affiliate link to earn per click

3. **Add a proper domain** — buy `flightdrop.com` (or similar) on
   Namecheap (~$12/year) and point it to your Railway app

---

## Common issues

**"ModuleNotFoundError"** — Run `pip install -r requirements.txt`

**"Amadeus API error 401"** — Double-check your Client ID and Secret in `.env`

**Emails not arriving** — Check your spam folder; verify your domain in Resend

**CORS error in browser** — Make sure `app.py` is running on port 5000
