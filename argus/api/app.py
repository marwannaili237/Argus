from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db
from api.routes import health, users, investigations, monitors, metrics, audit, templates, notes, webhooks, rss
from config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Argus OSINT API",
        description="Open Source Intelligence investigation platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Parse CORS origins from comma-separated config
    cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if not cors_origins:
        cors_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Route routers ---
    app.include_router(health.router, prefix="/api")
    app.include_router(metrics.router, prefix="/api")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(investigations.router, prefix="/api/v1")
    app.include_router(monitors.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")
    app.include_router(templates.router, prefix="/api/v1")
    app.include_router(notes.router, prefix="/api/v1")
    app.include_router(webhooks.router, prefix="/api/v1")
    app.include_router(rss.router, prefix="/api/v1")

    # --- Static files & dashboard ---
    import os
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def dashboard():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return {"message": "Argus OSINT API is running", "docs": "/docs"}

    return app
