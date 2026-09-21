# PulseGrid

Cloud-hosted movie-show availability monitor for India.

Track BookMyShow showtimes and get Telegram alerts when matching
sessions appear or change.

## What works (MVP)

- FastAPI jobs API + JWT auth
- Telegram bot commands (`/track`, `/jobs`, `/pause`, `/resume`, …)
- BookMyShow live retrieval (`curl_cffi` + Cloudflare session)
- Continuous worker with session dedupe + Telegram notifications
- Cities: Hyderabad, Mumbai, Bengaluru, Chennai, Delhi/NCR

## Quick start

### 1. Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
playwright install chromium
copy .env.example .env
# edit .env — DATABASE_URL, JWT_SECRET_KEY, TELEGRAM_BOT_TOKEN
```

### 2. Database

```powershell
alembic upgrade head
.\.venv\Scripts\python.exe scripts/create_admin.py
```

### 3. Cloudflare session (once, then when cookies expire)

Needs a visible browser window:

```powershell
.\.venv\Scripts\python.exe scripts/bootstrap_bms_session.py --city hyderabad
```

### 4. Run API + worker

Terminal A — API / Telegram webhook:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Point Telegram at your public URL (ngrok, etc.):

```powershell
.\.venv\Scripts\python.exe scripts/set_telegram_webhook.py
```

Terminal B — monitor loop:

```powershell
.\.venv\Scripts\python.exe scripts/run_worker.py
```

### 5. Create a job from Telegram

```text
/track
ET00514261
bookmyshow
Hyderabad
Any
2026-09-21
00:00
23:59
60
```

For BookMyShow, **Target must be the event code** (e.g. `ET00514261`), not the movie title. Theater `Any` matches all venues.

## Smoke tests

Fetch showtimes only:

```powershell
.\.venv\Scripts\python.exe scripts/fetch_bms_showtimes.py ET00514261 --language telugu
```

Provider + dedupe path (optional Telegram):

```powershell
.\.venv\Scripts\python.exe scripts/smoke_bms_monitor.py ET00514261 --theater Any
.\.venv\Scripts\python.exe scripts/smoke_bms_monitor.py ET00514261 --notify --chat-id YOUR_CHAT_ID
```

## Architecture

Provider retrieval is isolated from the worker/core:

```text
Telegram / API
      │
      ▼
TrackingJob (DB)
      │
      ▼
Worker loop ──► BookMyShowProvider ──► CurlCffiTransport
      │                                      │
      │                               primary-dynamic
      ▼
Dedupe seen sessions → Telegram alert
```

See `project-architecture.md` for the full roadmap.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
