# PulseGrid

Cloud-hosted movie-show availability monitoring system for India.

Track **BookMyShow** and **District** (`district.in`) showtimes in real-time. Get instant **Telegram alerts** and view live showtimes directly in the **Web UI Ops Console** when matching sessions open or change.

---

## 🚀 Key Features

- **Multi-Provider Support**: Live showtime tracking for both **BookMyShow** (`curl_cffi` TLS impersonation + Cloudflare session) and **District** (`district.in` Next.js SSR parser).
- **Automatic Embedded Worker**: Background poller automatically starts on FastAPI server launch (`ENABLE_EMBEDDED_WORKER=true`), supporting seamless single-container cloud deployment.
- **Indian Standard Time (IST) Standard**: All job schedules, polling logs, Telegram notifications, and UI displays default to **IST** (`Asia/Kolkata`, UTC+05:30).
- **Web UI Ops Console & Show Results Modal**: Built with React + TypeScript + Vite. Click any job to view live detected showtimes, cinema names, formats (2D/IMAX), and availability status.
- **Theater Management**: Match specific venues or select `Any` theater to monitor all venues across a city.
- **Telegram Integration**: Webhook & polling bot handlers (`/track`, `/jobs`, `/pause`, `/resume`, `/stop`, `/start`).
- **Supported Cities**: Hyderabad, Mumbai, Bengaluru, Chennai, Delhi/NCR, Gurgaon, and custom city slugs.

---

## 🛠️ Architecture Overview

```text
               User (Web UI / Telegram)
                         │
                         ▼
                   FastAPI API Server
                         │
         ┌───────────────┴───────────────┐
         │                               │
  REST Endpoints                 Embedded Worker Loop
  (/jobs, /watch, /results)       (Lifespan Task, 15s)
         │                               │
         └───────────────┬───────────────┘
                         │
                 PostgreSQL (Neon)
                         │
                 Provider Interface
            ┌────────────┴────────────┐
            │                         │
     BookMyShowProvider        DistrictProvider
     (curl_cffi + CF Jar)    (district.in SSR parser)
            │                         │
            └────────────┬────────────┘
                         ▼
             Normalized Session Results
                         │
         ┌───────────────┴───────────────┐
         │                               │
  Telegram Notification         Web UI Results Drawer
  (New session alerts)          (Full showtimes history)
```

---

## ⚡ Quick Start

### 1. Prerequisites & Installation

```powershell
# Clone repository
git clone https://github.com/your-username/pulsegrid.git
cd pulsegrid

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt
pip install -e .

# Install Playwright browser engines (for Cloudflare session bootstrap)
playwright install chromium

# Environment configuration
copy .env.example .env
```

Edit `.env` and set your credentials:
```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/pulsegrid
JWT_SECRET_KEY=your-secure-jwt-secret
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
ENABLE_EMBEDDED_WORKER=true
WORKER_POLL_SECONDS=15
```

### 2. Database Setup

```powershell
# Run Alembic migrations
alembic upgrade head

# Create initial admin user
.\.venv\Scripts\python.exe scripts/create_admin.py
```

### 3. Bootstrap Cloudflare Session (One-Time)

BookMyShow requires a Cloudflare clearance cookie (`cf_clearance`). Run the stealth bootstrap script once (requires a display window):

```powershell
.\.venv\Scripts\python.exe scripts/bootstrap_bms_session.py --city hyderabad
```

### 4. Run Application & Web UI

#### Option A: Production Mode (FastAPI serves bundled React Web UI + Embedded Worker)
```powershell
# Build React frontend
cd frontend
npm install
npm run build
cd ..

# Start FastAPI server
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
Open **http://127.0.0.1:8000/** to access the Web UI Ops Console.

#### Option B: Development Mode (Vite Hot-Reload on `:5173`)
```powershell
# Terminal A — Backend API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Terminal B — Frontend Dev Server
cd frontend
npm run dev
```
Open **http://127.0.0.1:5173/**.

---

## 📱 Telegram Integration

1. Set your public Webhook URL (e.g. via ngrok or production domain):
   ```powershell
   .\.venv\Scripts\python.exe scripts/set_telegram_webhook.py
   ```
2. Start tracking a movie via Telegram chat:
   ```text
   /track
   ET00514261
   bookmyshow
   Hyderabad
   Any
   2026-09-22
   00:00
   23:59
   60
   ```
   *Note*: For **BookMyShow**, pass the Event Code (e.g., `ET00514261`). For **District**, pass the Movie Code (e.g., `MV181196`) or full District URL.

---

## 🐳 Docker Deployment

```powershell
docker compose up --build
```
Services:
- `db` — PostgreSQL 16
- `api` — FastAPI REST API + Web UI on port `:8000` (auto-runs migrations)
- `worker` — Standalone worker service (optional if embedded worker is enabled)

---

## 🧪 Testing

Run the comprehensive pytest suite (170 tests):
```powershell
.\.venv\Scripts\python.exe -m pytest
```

---

## 📄 Documentation

For detailed architectural principles, provider normalization models, and technical decisions, see [project-architecture.md](project-architecture.md).
