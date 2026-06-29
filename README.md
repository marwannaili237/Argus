<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-0.138-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/aiogram-3-26A5E4?logo=telegram&logoColor=white" alt="aiogram 3">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/OSINT-90%20Plugins-orange" alt="90 Plugins">
  <img src="https://img.shields.io/badge/11%20Target%20Types-blueviolet" alt="11 Target Types">
  <img src="https://img.shields.io/badge/100%25-Free%20Sources-success" alt="Free Sources">
  <img src="https://img.shields.io/badge/Web%20Dashboard- included-9cf">
  <img src="https://img.shields.io/badge/CI%20CD-GitHub%20Actions-2088FF">
</p>

<h1 align="center">🦅 Argus</h1>

<p align="center">
  <strong>Free, Telegram-first Open Source Intelligence (OSINT) Investigation Platform</strong>
</p>

<p align="center">
  Submit a target via Telegram or the Web Dashboard — Argus automatically runs <strong>90 OSINT plugins</strong> against it, collecting data from free public sources. Optionally generates AI-powered threat intelligence reports via Google Gemini.
</p>

---

## Table of Contents

- [Features](#features)
- [Supported Targets](#supported-targets)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Docker Deployment](#docker-deployment)
- [Web Dashboard](#web-dashboard)
- [Architecture](#architecture)
- [Plugin Reference](#plugin-reference)
- [API Reference](#api-reference)
- [Telegram Bot Commands](#telegram-bot-commands)
- [Monitoring](#monitoring)
- [Investigation Workflow](#investigation-workflow)
- [Integrations](#integrations)
- [Development](#development)
- [License](#license)

---

## Features

### Core
- **90 OSINT Plugins** across 11 target types — the most comprehensive free OSINT toolkit available
- **100% Free Data Sources** — no paid APIs, no API keys required for core functionality
- **Telegram-Native Interface** — submit targets, view results, manage monitors via Telegram with inline keyboards
- **AI-Powered Reports** — Google Gemini synthesizes evidence into professional threat intelligence reports
- **Change Monitoring** — scheduled re-scans with SHA-256 fingerprint diffing and alerts
- **REST API** — full FastAPI backend with JWT authentication
- **Web Dashboard** — dark-themed SOC-style dashboard at `http://localhost:8000`

### Email OSINT (10 specialized plugins)
- **SMTP Verification** — connect to MX server to verify mailbox existence
- **Pattern Discovery** — find all emails at a domain via Google dorks, GitHub, Gravatar
- **Breach Timeline** — detailed breach history with dates, data types, and severity scoring
- **Identity Extraction** — cross-reference emails to find associated usernames, phones, addresses
- **Security Posture** — SPF/DMARC/DKIM validation with 0-100 scoring (A-F grade)
- **Age Estimation** — estimate email age from earliest breach appearances
- **Domain Profiling** — full analysis of the email's domain (RDAP, MX provider, free provider detection)
- **Username Correlation** — extract username from email and auto-check GitHub
- **Disposable Detection** — 500+ provider database with secondary signals
- **Reverse Search** — search paste sites, DuckDuckGo, GitHub, IntelX for the email

### Advanced OSINT (15 new plugins)
- **Google Dorking** — automated sensitive file/hidden path discovery
- **GitHub Dorking** — exposed secret and API key detection
- **Redirect Chain** — follow and analyze HTTP redirect hops
- **robots.txt/Sitemap** — discover hidden paths and site structure
- **SSL/TLS Analysis** — certificate details, HSTS, cipher suites
- **MAC Address Lookup** — OUI vendor identification
- **Crypto Tracer** — BTC/ETH address balance and transaction lookup
- **Onion Checker** — Tor/.onion equivalent detection
- **PDF Metadata** — document author, creation date, software extraction
- **DNSSEC Validation** — DNSSEC chain of trust verification
- **SPF/DMARC/DKIM** — email security posture for domains
- **Port Scanning** — comprehensive port and service detection
- **Technology Detection** — enhanced Wappalyzer-style tech fingerprinting
- **Social Post History** — recent activity from Reddit, GitHub, HackerNews
- **Shodan Dorking** — Shodan search queries for domains and IPs

### Investigation Workflow
- **Templates** — predefined plugin sets (full, quick, email_intel, brand, person)
- **Bulk Import** — investigate multiple targets at once (comma or newline separated)
- **Comparison** — diff two investigations on the same target
- **Chaining** — extract discovered targets from results and auto-investigate
- **Notes** — add analyst notes to any investigation
- **Progress Tracking** — real-time plugin-by-plugin progress in Telegram
- **Threat Level** — automatic 🟢 LOW / 🟡 MEDIUM / 🔴 HIGH / 🔴 CRITICAL scoring
- **Multi-Target** — `/investigate target1 target2 target3` runs all at once
- **Quick-Reply Keyboards** — tap-to-select target type buttons in Telegram


### Infrastructure
- **Prometheus Metrics** — `/api/metrics` endpoint for monitoring
- **Structured JSON Logging** — machine-parseable log output
- **API Rate Limiting** — sliding window rate limiter
- **Plugin Timeout** — per-plugin timeout enforcement
- **Plugin Retry** — automatic retry with exponential backoff
- **Result Caching** — TTL-based caching to avoid redundant lookups
- **Graceful Shutdown** — finish running investigations on SIGTERM
- **Data Retention** — auto-purge investigations older than N days
- **User Roles** — admin, analyst, viewer with permission checks
- **Audit Logging** — immutable log of all API actions

### Integrations
- **Webhook Notifications** — POST alerts to any URL (Slack, Discord, custom)
- **Slack Notifier** — send alerts to Slack webhooks
- **Discord Notifier** — send alerts to Discord webhooks
- **Email Notifications** — SMTP-based email alerts
- **Telegram Channel Broadcast** — send monitor alerts to Telegram channels
- **RSS Feed** — subscribe to investigation results via RSS
- **CI/CD** — GitHub Actions pipeline (lint, test, Docker build)
- **Docker HEALTHCHECK** — container health monitoring

## Supported Targets

| Target Type | Format | Example | Plugins |
|---|---|---|---|
| **Domain** | `example.com` | `google.com` | 26 |
| **URL** | `https://...` | `https://example.com/page` | 25 |
| **IP Address** | `x.x.x.x` | `8.8.8.8` | 10 |
| **Email** | `user@domain` | `admin@example.com` | 18 |
| **Username** | `@user` or `user` | `@johndoe` | 7 |
| **Phone** | `+123...` | `+14155552671` | 1 |
| **Image** | Image URL | `https://i.imgur.com/abc.png` | 1 |
| **Person** | `First Last` | `John Smith` | 2 |
| **Company** | `Company Name` | `Acme Corp` | 2 |
| **MAC Address** | `XX:XX:XX...` | `AA:BB:CC:DD:EE:FF` | 1 |
| **Crypto** | `0x...` / `1...` / `bc1...` | `0x742d...` | 1 |

## Quick Start

### Prerequisites

- Python 3.11+
- A Telegram bot token (get one from [@BotFather](https://t.me/botfather))

### 1. Clone and Install

```bash
git clone https://github.com/marwannaili237/Argus.git
cd Argus
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
cd argus
cp .env.example .env
# Edit .env — set at minimum:
#   TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 3. Run

```bash
cd argus
python main.py
```

The platform starts on `http://0.0.0.0:8000` with the Telegram bot and web dashboard.

### 4. Use It

**Telegram:** Open Telegram, find your bot, send `/investigate example.com`

**Web Dashboard:** Open `http://localhost:8000` in your browser

## Configuration

All configuration via environment variables (or `.env` file in `argus/`).

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | For bot | — | Telegram bot token from @BotFather |
| `TELEGRAM_BOT_NAME` | No | `ArgusOSINTBot` | Display name |
| `GEMINI_API_KEY` | No | — | Google Gemini API key for AI reports |
| `SESSION_SECRET` | No | Auto-generated | JWT signing secret |
| `ARGUS_DB_URL` | No | `sqlite+aiosqlite:///./argus.db` | Database URL |
| `API_PORT` | No | `8000` | FastAPI port |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |
| `MAX_CONCURRENT_INVESTIGATIONS` | No | `5` | Max parallel investigations |
| `INVESTIGATION_TIMEOUT_SECONDS` | No | `120` | Per-investigation timeout |
| `DATA_RETENTION_DAYS` | No | `90` | Auto-purge old investigations |
| `SMTP_HOST` | No | — | SMTP server for email notifications |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | No | — | SMTP username |
| `SMTP_PASSWORD` | No | — | SMTP password |
| `FROM_EMAIL` | No | — | Sender email address |

## Docker Deployment

```bash
cp argus/.env.example argus/.env
# Set TELEGRAM_BOT_TOKEN

docker compose up -d --build
```

The API, web dashboard, and Telegram bot are all available at `http://localhost:8000`. SQLite is persisted in a Docker volume.

## Web Dashboard

Access at `http://localhost:8000` — a dark-themed SOC-style single-page application with:
- **Dashboard** — stats cards, quick investigate, recent investigations
- **Investigations** — filterable list with status/type, expandable evidence view
- **Investigation Detail** — full evidence cards, AI report display, actions
- **Monitors** — create, pause/resume, delete monitors
- **Plugins** — browsable directory of all 90 plugins grouped by target type
- **Settings** — profile info, JWT token, API docs links


## Architecture

```
argus/main.py                          ─── Entry point (asyncio.gather)
  ├── run_api()                        ─── FastAPI + Uvicorn (:8000) + Web Dashboard
  ├── run_bot()                        ─── aiogram 3 Telegram bot (polling)
  ├── run_scheduler()                  ─── Monitor loop (5-min poll) + retention cleanup
  │
argus/api/                             ─── FastAPI REST API
  ├── app.py                           ─── App factory + static files + CORS
  ├── auth.py, deps.py                 ─── JWT auth + current user dependency
  ├── rate_limit.py                    ─── Sliding window rate limiter
  └── routes/
        ├── health.py                  ─── /api/health, /api/ready
        ├── users.py                   ─── Auth, profile
        ├── investigations.py          ─── CRUD + bulk + compare + chain + templates
        ├── monitors.py                ─── CRUD + check-now
        ├── templates.py               ─── Investigation templates
        ├── notes.py                   ─── Investigation notes
        ├── webhooks.py                ─── Webhook CRUD
        ├── rss.py                     ─── RSS feed output
        ├── audit.py                   ─── Audit log (admin)
        └── metrics.py                 ─── Prometheus metrics
  │
argus/bot/                             ─── Telegram Bot (aiogram 3)
  └── handlers/
        ├── start.py                   ─── /start, /help + quick-reply keyboards
        ├── investigate.py             ─── /investigate (multi-target), /status
        ├── results.py                 ─── /results, /analyze, /history
        ├── monitor.py                 ─── /monitor, /monitors, /unmonitor, /checkmon
        ├── bulk.py                    ─── /bulk
        ├── notes.py                   ─── /note
        └── callbacks.py               ─── Inline keyboard callbacks
  │
argus/plugins/                         ─── 90 OSINT Plugins
  ├── base.py, runner.py, templates.py
  ├── timeout.py, retry.py           ─── Plugin wrappers
  └── *_plugin.py (46 files)         ─── Concrete plugins
  │
argus/
  ├── config.py, database.py, models.py
  ├── cache.py                        ─── TTL-based result cache
  ├── logging_config.py              ─── Structured JSON logging
  ├── retention.py                   ─── Data retention cleanup
  ├── monitor_scheduler.py           ─── SHA-256 fingerprint + diff + alerts
  ├── notifiers/                     ─── Webhook, Slack, Discord, Email
  └── static/index.html              ─── Web Dashboard SPA
```

## Plugin Reference

### Domain / URL Plugins

| Plugin | Sources |
|---|---|
| WHOIS | RDAP/WHOIS registry |
| DNS | System resolver (A, AAAA, MX, NS, TXT, CNAME) |
| Cert Transparency | crt.sh |
| IP Geolocation | ip-api.com |
| HTTP Metadata | Direct HTTP (title, tech, security headers) |
| Shodan InternetDB | Shodan InternetDB + HackerTarget |
| Shodan Dorking | Shodan search queries |
| Wayback Machine | Internet Archive CDX API |
| BGP / ASN | bgpview.io + RIPE NCC |
| Threat Intel | URLHaus, PhishTank, TOR exits, Spamhaus, AbuseIPDB |
| Subdomains | HackerTarget, RapidDNS, ViewDNS, crt.sh, DNS brute-force |
| Passive DNS | HackerTarget, ViewDNS |
| Paste / Leaks | GitHub, Pastebin, psbdmp.ws, IntelX, DeHashed |
| GitHub OSINT | GitHub Search API |
| Google Dorking | DuckDuckGo (filetype, inurl, intitle, site operators) |
| GitHub Dorking | GitHub code search for secrets |
| Redirect Chain | Manual 301/302 following |
| robots.txt / Sitemap | Direct fetch and parse |
| SSL/TLS Analysis | ssl module (cert details, cipher suites) |
| DNSSEC | DNSKEY/DS record validation |
| SPF/DMARC/DKIM | TXT record parsing and validation |
| Port Scanning | Shodan + HackerTarget Nmap |
| Technology | Wappalyzer-style header/body detection |
| Email Patterns | DuckDuckGo dorks, GitHub, Gravatar enumeration |
| Email Security | SPF/DMARC/DKIM parsing + blacklist check |

### Email Plugins

| Plugin | Sources |
|---|---|
| Email Intel | EmailRep.io, Gravatar, MX records, GitHub, Trumail |
| Breach Check | LeakCheck.io, EmailRep.io, HIBP |
| Social Email | 11 platforms (Twitter/X, Instagram, GitHub, Spotify, etc.) |
| SMTP Verification | Direct MX server connection |
| Email Patterns | DuckDuckGo, GitHub, Gravatar prefix enumeration |
| Breach Timeline | LeakCheck.io, EmailRep.io, Hudson Rock |
| Email Identity | GitHub, LinkedIn (DuckDuckGo), Hudson Rock |
| Email Security | SPF/DMARC/DKIM + Spamhaus ZEN + MX provider detection |
| Email Age | Hudson Rock, LeakCheck, GitHub, Gravatar |
| Email Domain Profile | RDAP, MX records, DNS, 37 free provider database |
| Email Username | GitHub API (username variations from email local part) |
| Disposable Detection | 500+ provider database + MX + RDAP age |
| Email Reverse Search | psbdmp.ws, DuckDuckGo, GitHub, IntelX |

### Username / Profile Plugins

| Plugin | Sources |
|---|---|
| Username Hunt | 48 platforms (Sherlock-style HTTP probing) |
| Profile Deep Dive | GitHub, Reddit, HackerNews, Twitter/X, Dev.to, Keybase |
| Social Posts | Reddit RSS, GitHub events, HackerNews submissions |

### Entity / Other Plugins

| Plugin | Sources |
|---|---|
| Entity Intel | OpenCorporates, Google News, SEC EDGAR, DuckDuckGo, LinkedIn, TruePeopleSearch |
| Phone Intel | phonenumbers, Numverify, AbstractAPI |
| Image Forensics | Pillow EXIF, reverse search links |
| MAC Lookup | IEEE OUI database |
| Crypto Tracer | blockchain.info (BTC), Etherscan (ETH) |
| Onion Checker | Tor2web proxies, Ahmia.fi, Tor66 |
| PDF Metadata | Binary PDF header parsing |
| AI Analysis | Google Gemini 2.0 Flash (optional) |

## API Reference

### Core
| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Web Dashboard |
| GET | `/api/health` | Health check |
| GET | `/api/ready` | Readiness check |
| GET | `/api/metrics` | Prometheus metrics |
| GET | `/docs` | Swagger API docs |
| GET | `/redoc` | ReDoc API docs |

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/users/auth/telegram` | Register/login via Telegram ID → JWT |
| GET | `/api/v1/users/me` | Current user profile |

### Investigations
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/investigations` | Start investigation (optional `template` field) |
| POST | `/api/v1/investigations/bulk` | Bulk create (up to 50 targets) |
| GET | `/api/v1/investigations` | List investigations |
| GET | `/api/v1/investigations/{id}` | Get investigation + evidence |
| POST | `/api/v1/investigations/{id}/analyze` | Generate AI report |
| GET | `/api/v1/investigations/{id1}/compare/{id2}` | Compare two investigations |
| POST | `/api/v1/investigations/{id}/chain` | Chain: extract and investigate discovered targets |
| POST | `/api/v1/investigations/{id}/notes` | Add analyst note |
| GET | `/api/v1/investigations/{id}/notes` | List notes |

### Monitors
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/monitors` | Create monitor |
| GET | `/api/v1/monitors` | List monitors |
| PATCH | `/api/v1/monitors/{id}` | Update (pause/resume/schedule) |
| DELETE | `/api/v1/monitors/{id}` | Delete |
| POST | `/api/v1/monitors/{id}/check-now` | Force immediate check |

### Templates
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/templates` | List all investigation templates |

### Other
| Method | Endpoint | Description |
|---|---|---|
| GET/POST/DELETE | `/api/v1/webhooks` | Webhook CRUD |
| GET | `/api/v1/audit-logs` | Audit log (admin, paginated) |
| GET | `/api/v1/users/{id}/rss?key={jwt}` | RSS feed of investigations |

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Register + quick-reply keyboard |
| `/help` | All commands and supported targets |
| `/investigate <target>` | OSINT scan (multi-target: space-separated) |
| `/bulk <targets>` | Bulk investigation (comma/newline separated) |
| `/status <id>` | Check progress |
| `/results <id>` | View summary |
| `/analyze <id>` | AI threat report |
| `/history` | Last 10 investigations |
| `/monitor <target> [schedule]` | Create monitor (hourly/daily/weekly) |
| `/monitors` | List monitors with controls |
| `/unmonitor <id>` | Delete monitor |
| `/checkmon <id>` | Force check |
| `/note <id> <text>` | Add analyst note |

## Monitoring

1. Create a monitor with `/monitor example.com daily`
2. Scheduler polls every 5 minutes for due monitors
3. Fresh investigation runs automatically
4. SHA-256 fingerprints of key metrics (subdomains, CVEs, ports, DNS, threats, social accounts)
5. Telegram alerts + webhook notifications on changes
6. Detected changes: subdomains, CVEs, ports, breaches, reputation, DNS, certificates

## Investigation Workflow

### Templates
Use `template` field when creating investigations: `full`, `quick`, `email_intel`, `brand`, `person`

### Chaining
After an investigation completes, `/chain <id>` extracts discovered targets (subdomains, IPs, emails) and creates new investigations for each.

### Comparison
`/api/v1/investigations/{id1}/compare/{id2}` returns a side-by-side diff of evidence between two investigations on the same target.

## Integrations

### Webhooks
Create webhooks via API or monitor creation. Events: `investigation_complete`, `monitor_alert`. Compatible with Slack, Discord, Zapier, n8n, and any HTTP endpoint.

### Slack/Discord
Use webhook URLs to post alerts. The `send_to_slack()` and `send_to_discord()` helpers format messages appropriately for each platform.

### Email Notifications
Configure SMTP settings to receive investigation completions and monitor alerts via email.

### RSS
Subscribe to `GET /api/v1/users/{id}/rss?key={jwt}` in any RSS reader for real-time investigation updates.

## Development

### Running Tests

```bash
pip install -e ".[dev]"
PYTHONPATH=argus pytest tests/ -v
```

### CI/CD
GitHub Actions runs on push/PR: lint (ruff), test (pytest), Docker build.

### Adding a Plugin
1. Create `argus/plugins/my_plugin.py` extending `BasePlugin`
2. Implement `async run(target: str) -> PluginResult`
3. Import and register in `runner.py` ALL_PLUGINS
4. Add summary builder in `_build_summary()`

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
