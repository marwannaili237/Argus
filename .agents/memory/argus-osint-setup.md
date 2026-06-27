---
name: Argus OSINT setup
description: Key decisions and gotchas for the Argus OSINT platform (Python FastAPI + aiogram bot in argus/ directory)
---

## Rule
Use `ARGUS_DB_URL` (not `DATABASE_URL`) in config.py for the database connection string.

**Why:** The Replit environment has `DATABASE_URL` set to a managed PostgreSQL instance used by the TypeScript api-server artifact. pydantic-settings auto-reads env vars by field name, so naming the field `database_url` caused SQLAlchemy to try to connect to Postgres and fail with `ModuleNotFoundError: No module named 'psycopg2'`.

**How to apply:** Always keep the config field named `argus_db_url` and the env var `ARGUS_DB_URL`. Default is SQLite (`sqlite+aiosqlite:///./argus.db`).

## Architecture
- Single Python process: FastAPI (uvicorn, port 8000) + aiogram polling run as concurrent asyncio tasks in `main.py`
- Artifact.toml for api-server updated to route `/api` → port 8000 (Python server)
- Workflow name: `Argus OSINT`, command: `cd argus && python main.py`
- Bot requires `TELEGRAM_BOT_TOKEN` secret; without it, only the API starts (graceful degradation)
- SQLite DB file created at `argus/argus.db` on first run

## Plugins (all free, no API keys)
1. whois — python-whois library (sync, run_in_executor)
2. dns — dnspython (async parallel per record type)
3. certs — crt.sh JSON API
4. ip_geo — ip-api.com free JSON API
5. http — direct aiohttp fetch with tech detection
