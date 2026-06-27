"""
Argus OSINT Platform — Entry Point
Runs FastAPI and Telegram bot concurrently.
"""
import asyncio
import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("argus")

sys.path.insert(0, os.path.dirname(__file__))

from config import get_settings

settings = get_settings()


async def run_api():
    import uvicorn
    from api.app import create_app
    app = create_app()
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=settings.api_port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_bot():
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot will not start. Set it to enable the Telegram interface.")
        return

    await asyncio.sleep(2)
    from bot.main import start_bot
    try:
        await start_bot(settings.telegram_bot_token)
    except Exception as e:
        logger.error(f"Bot error: {e}")


async def main():
    logger.info("Starting Argus OSINT Platform")
    logger.info(f"API → http://0.0.0.0:{settings.api_port}")
    if settings.telegram_bot_token:
        logger.info("Telegram bot → enabled")
    else:
        logger.info("Telegram bot → disabled (set TELEGRAM_BOT_TOKEN to enable)")

    await asyncio.gather(run_api(), run_bot())


if __name__ == "__main__":
    asyncio.run(main())
