# Argus OSINT Platform

A free, Telegram-first Open Source Intelligence (OSINT) investigation platform. Users submit a target (domain, IP, URL) via Telegram and Argus automatically runs OSINT plugins against it — WHOIS, DNS, certificate transparency, IP geolocation, and HTTP metadata — all from free public data sources with no credit card required.

## Run & Operate

- `cd argus && python main.py` — run the full platform (API + Telegram bot)
- The workflow `Argus OSINT` starts this automatically

## Stack

- Python 3.11, FastAPI, Uvicorn
- aiogram 3 — Telegram bot framework
- SQLAlchemy 2 (async) + SQLite (via aiosqlite)
- aiohttp — async HTTP for OSINT plugins
- dnspython — DNS record lookups
- python-whois — WHOIS lookups
- python-jose — JWT auth

## Where things live

- `argus/main.py` — entry point (starts API + bot concurrently)
- `argus/config.py` — all settings, reads from env vars
- `argus/database.py` — SQLAlchemy async engine (SQLite)
- `argus/models.py` — User, Investigation, Evidence ORM models
- `argus/api/` — FastAPI application
  - `api/app.py` — app factory + lifespan
  - `api/auth.py` — JWT creation/validation
  - `api/deps.py` — FastAPI dependencies (current user)
  - `api/routes/` — health, users, investigations
- `argus/bot/` — Telegram bot (aiogram 3)
  - `bot/handlers/start.py` — /start, /help
  - `bot/handlers/investigate.py` — /investigate, /status
  - `bot/handlers/results.py` — /results, /history
- `argus/plugins/` — OSINT plugin system
  - `plugins/base.py` — BasePlugin protocol
  - `plugins/whois_plugin.py` — WHOIS/RDAP
  - `plugins/dns_plugin.py` — DNS records (A, AAAA, MX, NS, TXT, CNAME)
  - `plugins/certs_plugin.py` — Certificate transparency via crt.sh
  - `plugins/ip_plugin.py` — IP geolocation via ip-api.com
  - `plugins/http_plugin.py` — HTTP metadata (title, stack detection)
  - `plugins/runner.py` — target classifier + parallel plugin orchestrator

## API Endpoints

- `GET /api/health` — health check
- `POST /api/v1/users/auth/telegram` — register/login via Telegram ID → JWT
- `GET /api/v1/users/me` — current user profile
- `POST /api/v1/investigations` — start investigation
- `GET /api/v1/investigations` — list user's investigations
- `GET /api/v1/investigations/{id}` — get investigation + evidence

## Architecture decisions

- **Single Python process** runs both FastAPI (uvicorn) and the Telegram bot (aiogram polling) as concurrent asyncio tasks — eliminates inter-service complexity for MVP.
- **SQLite for MVP** — using `ARGUS_DB_URL` env var (not `DATABASE_URL`) to avoid conflict with the Replit-managed Postgres used by other artifacts.
- **No Celery/Redis** — investigation plugins run as `asyncio.gather` background tasks within FastAPI's `BackgroundTasks`. Clean, no broker needed.
- **All OSINT sources are free** — no paid proxies, no paid APIs. Plugins use: RDAP/WHOIS (free), DNS (system resolver), crt.sh (free API), ip-api.com (free tier), direct HTTP.
- **JWT auth tied to Telegram ID** — bot authenticates by posting `telegram_id` to `/api/v1/users/auth/telegram` and gets a JWT back. No passwords.

## Product

- Start an OSINT investigation via `/investigate <target>` in Telegram
- The bot shows live progress and auto-updates the message when done
- Targets supported: domains, URLs, IP addresses
- Free plugins: WHOIS · DNS · Certificate Transparency · IP Geolocation · HTTP metadata
- Commands: /start · /help · /investigate · /status · /results · /history

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Use `ARGUS_DB_URL` (not `DATABASE_URL`) to set the database URL — avoids picking up the Replit-managed PostgreSQL URL
- Bot requires `TELEGRAM_BOT_TOKEN` env secret — without it, only the API runs
- `cd argus && python main.py` must be run from the workspace root (argus/ is a subdirectory)
- Plugin results are stored as JSON blobs in the `evidence` table

## Pointers

- See `argus/.env.example` for required environment variables
- OSINT spec docs are in `/tmp/unzipped_project/argus-design/docs/` (36 docs covering the full production architecture)
