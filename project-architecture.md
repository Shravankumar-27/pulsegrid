Absolutely. Here is the **full PulseGrid architecture and roadmap**, from the very beginning to where we are now, including why we took each step and what we're doing next.

# PulseGrid — Complete Architecture & Roadmap

## 1. What we are actually building

PulseGrid is a **cloud-hosted movie-show availability monitoring system** for India.

The core idea:

```text
User
 │
 ├── Web Dashboard
 │
 └── Telegram Bot
        │
        ▼
     PulseGrid
        │
        ├── BookMyShow
        └── District
             │
             ▼
       Monitor movie/show
             │
             ▼
      Detect new/changed shows
             │
             ▼
        Notify user
```

The user should eventually be able to say something like:

```text
Track:
Movie: Mandalorian and Grogu
Platform: BookMyShow + District
City: Hyderabad
Date: 19 Sep
Theatre: Any
Start monitoring: Now
Stop monitoring: 19 Sep 11:59 PM
```

PulseGrid continuously watches the provider and sends a notification when something changes.

---

# 2. The important engineering principle

We deliberately split PulseGrid into **two completely different problems**:

### Problem A — Provider retrieval

> How do we reliably get the latest show information from BookMyShow/District?

### Problem B — PulseGrid itself

> What do we do with that information?

This distinction is extremely important.

We don't want this:

```text
PulseGrid
   ↓
hardcoded BMS API
   ↓
everything depends on it
```

Instead:

```text
             PulseGrid Core
                  │
          Provider Interface
           /              \
          /                \
 BookMyShow Provider    District Provider
          │                │
          ▼                ▼
     BMS retrieval     District retrieval
```

If BMS changes tomorrow, we modify the BMS provider—not the entire application.

---

# 3. Phase 1 — Project foundation

We started by creating the project as a proper backend application rather than a random script.

Current technology direction:

```text
Python 3.12
     │
     ▼
FastAPI
     │
     ├── PostgreSQL
     ├── SQLAlchemy
     ├── Alembic
     ├── JWT authentication
     ├── HTTPX
     ├── Telegram Bot API
     ├── pytest
     ├── Docker
     └── GitHub Actions
```

Repository workflow:

```text
develop
   │
   ├── development
   ├── testing
   └── feature work
        │
        ▼
      stable
        │
        ▼
      main
```

And your preferred milestone workflow is:

```text
Lesson / technology milestone
          ↓
implement
          ↓
pytest
          ↓
Git commit
          ↓
continue
```

We are **not merging unfinished experiments into `main`**.

---

# 4. Phase 2 — Database architecture

We created the foundation for users and monitoring jobs.

Conceptually:

```text
User
 │
 ├── id
 ├── username/email
 ├── authentication
 ├── role
 │
 └── TrackingJobs
          │
          ├── movie
          ├── platform
          ├── city
          ├── theatre
          ├── target_date
          ├── start_at
          ├── end_at
          ├── poll_interval
          └── status
```

A job represents:

> "Watch this thing until this time."

---

# 5. Phase 3 — Authentication

We implemented:

```text
User
  │
  ▼
Login
  │
  ▼
JWT
  │
  ▼
Authenticated API
```

And access control:

```text
Normal user
   ↓
own jobs

Admin
   ↓
administrative access
```

This gives us the foundation for a multi-user monitoring service.

---

# 6. Phase 4 — Job lifecycle

We then implemented the job state machine.

Conceptually:

```text
                 ┌──────────┐
                 │ PENDING  │
                 └────┬─────┘
                      │ start
                      ▼
                 ┌──────────┐
                 │ RUNNING  │
                 └────┬─────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
        pause       stop       expiry
          │           │           │
          ▼           ▼           ▼
       PAUSED       STOPPED   COMPLETED
          │
        resume
          │
          └──────────────► RUNNING
```

This is important because the worker shouldn't have to invent job behavior.

The database tells the worker:

```text
PENDING
RUNNING
PAUSED
STOPPED
COMPLETED
```

---

# 7. Phase 5 — REST API

We then exposed the job system through FastAPI.

Conceptually:

```text
POST   /jobs
GET    /jobs
GET    /jobs/{id}
PATCH  /jobs/{id}
DELETE /jobs/{id}

POST   /jobs/{id}/start
POST   /jobs/{id}/pause
POST   /jobs/{id}/resume
POST   /jobs/{id}/stop
```

And we added tests around authentication, ownership, lifecycle and security.

This gave us our first real PulseGrid backend.

---

# 8. Phase 6 — Telegram

Then we added the Telegram integration.

Current concept:

```text
Telegram
    │
    ▼
Telegram Bot API
    │
    ▼
/api/v1/telegram/webhook
    │
    ▼
PulseGrid
```

The bot is:

```text
PulseGridAlertBot
```

The important architectural decision was to use a **webhook**, rather than continuously polling Telegram.

Eventually:

```text
User
 │
 ▼
Telegram
 │
 ▼
Webhook
 │
 ▼
FastAPI
 │
 ▼
Job Service
 │
 ▼
Database
```

---

# 9. Phase 7 — Worker engine

This is where we are currently building the actual monitoring engine.

The worker's job is fundamentally:

```text
Find active jobs
      ↓
Determine whether they should run
      ↓
Retrieve provider data
      ↓
Normalize it
      ↓
Compare with previous state
      ↓
Detect changes
      ↓
Notify
      ↓
Repeat
```

At the moment we're working on the worker foundation.

For example:

```python
complete_expired_jobs()
```

which handles:

```text
RUNNING
   ↓
target time expired?
   ↓
YES
   ↓
COMPLETED
```

We hit the timezone bug:

```text
offset-naive
      vs
offset-aware
```

That is part of getting the worker foundation correct before connecting real providers.

---

# 10. Phase 8 — Provider research

This is the **major phase we're in now**.

Initially we thought:

```text
BMS
 ↓
HTTP API
 ↓
JSON
```

And your HAR investigation found something extremely valuable:

```text
/api/movies-data/v5/showtimes-by-event/primary-dynamic
```

with:

```text
eventCode
dateCode
regionCode
```

and a successful:

```text
HTTP 200
~517 KB
```

response.

That proved something important:

> The BMS frontend really does receive structured showtime data from an internal API.

But we then tried to reproduce it ourselves.

---

# 11. Experiment #1 — Direct API request

We tried:

```text
Playwright
   │
   ├── open BMS page
   │
   └── context.request.get()
             │
             ▼
       primary-dynamic
```

Result:

```text
HTTP 403
Cloudflare
```

This taught us:

> Having the correct URL and parameters is not sufficient.

---

# 12. Experiment #2 — Chromium browser's network

Next we tried letting the actual BMS page make the request.

But:

```text
Chromium
   ↓
BMS movie page
   ↓
Book tickets locator
   ↓
0 elements
```

So the browser never entered the booking flow.

Therefore we couldn't yet observe the real showtime request.

---

# 13. Experiment #3 — Firefox

We then checked current GitHub implementations.

This was a very important discovery.

Recent BMS monitoring implementations report that:

```text
curl
    → Cloudflare

Node HTTP
    → Cloudflare

Chromium
    → Cloudflare / inconsistent

Firefox
    → BMS works
```

And they use the **actual rendered booking flow** rather than relying entirely on undocumented API endpoints.

We tested Firefox ourselves.

Result:

```text
Firefox
   ↓
BMS
   ↓
Movie page successfully loaded
   ↓
"In cinemas"
"2D"
"IMAX 2D"
"DOLBY CINEMA 2D"
"Book tickets"
```

So:

# Firefox is working

That's our biggest provider-research result so far.

---

# 14. Where we are RIGHT NOW

Retrieval for BookMyShow is **solved and wired into the provider layer**.

```text
                        PulseGrid
                            │
                     Worker Engine
                            │
                    Provider Layer
                            │
                    ┌───────┴───────┐
                    │               │
              BookMyShow        District
                    │            (later)
                    ▼
            BookMyShowClient
                    │
            CurlCffiTransport   ← production default
                    │
         ┌──────────┴──────────┐
         │                     │
   cf_clearance jar      headed Chromium
   (disk session)        bootstrap on 403
         │                     │
         └──────────┬──────────┘
                    ▼
         primary-dynamic HTTP 200
                    ▼
         extract_sessions → AvailabilityResult
```

Proven live results (Hyderabad):

```text
ET00514261 → 171 sessions / 69 venues
ET00442702 →   8 sessions /  5 venues
```

Key files:

```text
app/services/providers/bms_session.py          CF cookie jar + bootstrap
app/services/providers/curl_cffi_transport.py  Chrome TLS API transport
app/services/providers/bookmyshow_client.py    default → CurlCffiTransport
app/services/providers/bookmyshow.py           parse / match / AvailabilityResult
scripts/fetch_bms_showtimes.py                 thin CLI over the same stack
```

---

# 15. What we learned (retrieval research)

1. Direct httpx/Playwright `context.request` → Cloudflare **403** (wrong TLS fingerprint).
2. Headless Chromium → CF challenge. Headed Chromium + stealth → obtains `cf_clearance`.
3. Buytickets page often **SSR's** showtimes into `__INITIAL_STATE__` and does **not** re-fire `primary-dynamic` — so XHR interception is unreliable.
4. With a valid `cf_clearance`, **`curl_cffi` Chrome impersonation** calls `primary-dynamic` successfully in ~3s.

---

# 16. Chosen retrieval strategy — Hybrid (Strategy C)

```text
                 BookMyShowProvider
                         │
                BookMyShowClient
                         │
                CurlCffiTransport
                         │
              ┌──────────┴──────────┐
              │                     │
       Fast API (curl_cffi)   Headed Chromium
       + saved CF cookies     session bootstrap
              │                     │
              └──────────┬──────────┘
                         ▼
                  primary-dynamic JSON
                         ▼
                  extract_sessions()
                         ▼
                  AvailabilityResult
```

`PlaywrightTransport` (Firefox XHR intercept) remains injectable as an experimental fallback, not the default.

---

# 17. Normalization layer

This is one of the most important pieces.

BMS might return:

```json
{
    "venueCode": "...",
    "sessionId": "...",
    "showTime": "...",
    "availStatus": 3
}
```

District might return something completely different.

PulseGrid shouldn't care.

We convert both into our own model:

```text
Show
 ├── provider
 ├── movie_id
 ├── movie_name
 ├── city
 ├── venue_id
 ├── venue_name
 ├── show_id
 ├── start_time
 ├── format
 ├── language
 ├── availability
 └── observed_at
```

Then:

```text
BMS JSON ────────┐
                 │
                 ▼
           Normalizer
                 │
District JSON ───┘
                 │
                 ▼
            PulseGrid Show
```

This is what makes multi-provider monitoring possible.

---

# 18. Change detection

Once we can retrieve shows, the worker doesn't need to notify on every poll.

It compares:

```text
Previous snapshot
       ↓
Current snapshot
       ↓
Diff
```

Example:

### Initial state

```text
PVR Hyderabad

10:00 AM
02:00 PM
06:30 PM
```

Later:

```text
PVR Hyderabad

10:00 AM
02:00 PM
04:15 PM   ← NEW
06:30 PM
```

PulseGrid detects:

```text
NEW SHOW
04:15 PM
```

and generates an event:

```text
ShowAdded
```

Similarly:

```text
ShowRemoved
ShowChanged
AvailabilityChanged
```

---

# 19. Availability monitoring

This is where your original requirement gets more interesting.

You specifically wanted to detect things like:

> A show is already released, then BMS suddenly opens another set of seats/rows.

So eventually we don't only track:

```text
show exists / doesn't exist
```

We track:

```text
Show
  │
  └── Session
        │
        ├── availability state
        ├── seat/row information
        └── observed timestamp
```

Potential state:

```text
SHOW CREATED
     ↓
SEATS CLOSED
     ↓
SEATS OPEN
     ↓
MORE SEATS OPENED
     ↓
SEATS SOLD
```

Then PulseGrid can notify based on the exact condition the user wants.

---

# 20. Polling engine

A tracking job might say:

```text
poll_interval = 60 seconds
```

Then:

```text
Worker
  │
  ├── Job #1 → BMS → every 60 sec
  │
  ├── Job #2 → District → every 30 sec
  │
  └── Job #3 → BMS → every 120 sec
```

But the worker shouldn't blindly hammer BMS.

Eventually we'll introduce:

```text
rate limiting
backoff
provider limits
concurrency limits
browser session reuse
```

This becomes especially important because Cloudflare protection exists.

---

# 21. Notification system

Once change detection works:

```text
Change detected
      │
      ▼
Notification event
      │
      ▼
Telegram
```

Example:

```text
🎬 New Show Detected

Mandalorian and Grogu

📍 AMB Cinemas: Gachibowli
🕐 7:25 PM
🎞️ IMAX 2D
🌐 BookMyShow

A new show has appeared.
```

Later we can support:

```text
new show
show removed
availability opened
specific seat/row opened
showtime changed
```

---

# 22. Telegram eventually becomes a real control plane

Instead of only notifications:

```text
Telegram
```

will eventually be able to create/manage jobs.

For example:

```text
/user
/track
/jobs
/pause
/resume
/stop
/status
```

Potentially:

```text
/track Mandalorian
```

followed by an interactive configuration flow.

Architecture:

```text
Telegram
   │
   ▼
Webhook
   │
   ▼
Command Handler
   │
   ▼
Job Service
   │
   ▼
PostgreSQL
```

The worker then consumes those jobs.

---

# 23. Web dashboard

Eventually:

```text
                    PulseGrid
                       │
          ┌────────────┴────────────┐
          │                         │
       Telegram                  Dashboard
          │                         │
          └────────────┬────────────┘
                       ▼
                   FastAPI
                       │
          ┌────────────┼────────────┐
          │            │            │
        Auth         Jobs       Monitoring
          │            │            │
          └────────────┼────────────┘
                       ▼
                  PostgreSQL
```

Dashboard can show:

```text
Active Jobs
Completed Jobs
Provider
Movie
Theatre
Next poll
Last successful poll
Last change
Status
```

---

# 24. Cloud deployment

The final system should **not depend on your laptop**.

Eventually:

```text
                    Internet
                       │
          ┌────────────┴────────────┐
          │                         │
       Telegram                  Browser
          │                         │
          └────────────┬────────────┘
                       │
                 Cloud deployment
                       │
              ┌────────┴────────┐
              │                 │
           FastAPI          Worker(s)
              │                 │
              └────────┬────────┘
                       │
                  PostgreSQL
```

With:

```text
Docker
GitHub Actions
environment variables/secrets
database migrations
logging
monitoring
```

and free/low-cost cloud infrastructure where practical.

---

# 25. Final architecture

When everything is complete, the conceptual architecture is:

```text
                         ┌─────────────────────┐
                         │       USERS         │
                         └──────────┬──────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
                Telegram                      Web Dashboard
                     │                             │
                     └──────────────┬──────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │                     │
                         │ Auth                │
                         │ Jobs API            │
                         │ Telegram Webhook    │
                         │ Admin               │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    PostgreSQL       │
                         │                     │
                         │ Users               │
                         │ Tracking Jobs        │
                         │ Snapshots            │
                         │ Events               │
                         │ Notifications        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Worker Engine    │
                         │                     │
                         │ Scheduler           │
                         │ Polling             │
                         │ Expiry              │
                         │ Retry/Backoff       │
                         └──────────┬──────────┘
                                    │
                          Provider Interface
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
          ┌──────────────────┐            ┌──────────────────┐
          │ BookMyShow       │            │ District         │
          │ Provider         │            │ Provider         │
          │                  │            │                  │
          │ Firefox/browser  │            │ browser/API      │
          │ API if possible  │            │ TBD              │
          │ DOM fallback     │            │                  │
          └────────┬─────────┘            └────────┬─────────┘
                   │                               │
                   └──────────────┬────────────────┘
                                  ▼
                         ┌─────────────────────┐
                         │     Normalizer      │
                         │                     │
                         │ Show                │
                         │ Session             │
                         │ Venue               │
                         │ Availability        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Change Detector    │
                         │                     │
                         │ New show            │
                         │ Changed show        │
                         │ Availability        │
                         │ Seat/row changes    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Notification Engine  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                              Telegram
```

---

# 26. Our exact roadmap from TODAY

```text
DONE — BMS MVP monitor
  ✅ BMS primary-dynamic retrieval (curl_cffi + CF session)
  ✅ BookMyShowProvider → AvailabilityResult
  ✅ Worker cycle + continuous run_worker.py loop
  ✅ Session dedupe with persisted WorkerState
  ✅ Telegram /track auto-starts RUNNING jobs
  ✅ Theater "Any" matches all venues
  ✅ Cities: HYD / Mumbai / Bengaluru / Chennai / Delhi
  ✅ smoke_bms_monitor.py + bootstrap_bms_session.py
  ✅ README runbook

NEXT (post-MVP)
     │
     ▼
① Admin / React dashboard
     │
     ▼
② Cloud deployment hardening

DONE recently
  ✅ Shared PulseGrid Show normalizer
  ✅ DistrictProvider (SSR pageProps → sessions)
  ✅ Multi-provider UX (platform allowlist + Telegram tips)
  ✅ Docker Compose (api + worker + db)
  ✅ GitHub Actions CI (pytest)
```

### The most important thing

**A working BookMyShow monitor is runnable end-to-end.**

```text
bootstrap_bms_session.py  →  cf_clearance
run_worker.py             →  poll RUNNING jobs
BookMyShowProvider        →  live showtimes
Telegram                  →  alert on new sessions
```

Keep provider-specific code inside `app/services/providers/`. Core worker
and job APIs stay provider-agnostic.
