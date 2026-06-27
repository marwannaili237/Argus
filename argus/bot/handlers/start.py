from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
import aiohttp
from config import get_settings

router = Router()
settings = get_settings()
API_BASE = f"http://localhost:{settings.api_port}/api/v1"


async def get_or_create_token(message: Message) -> str | None:
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "telegram_id": message.from_user.id,
                "username": message.from_user.username,
                "full_name": message.from_user.full_name,
            }
            async with session.post(f"{API_BASE}/users/auth/telegram", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("access_token")
    except Exception:
        pass
    return None


@router.message(CommandStart())
async def cmd_start(message: Message):
    token = await get_or_create_token(message)
    name = message.from_user.first_name or "there"

    if token:
        text = (
            f"👁 *Welcome to Argus OSINT, {name}!*\n\n"
            "I'm your open-source intelligence assistant. Give me a target and I'll investigate it using free, public data sources.\n\n"
            "*What I can investigate:*\n"
            "• 🌐 Domains (example.com)\n"
            "• 🔗 URLs (https://example.com)\n"
            "• 🖥 IP addresses (1.2.3.4)\n\n"
            "*Commands:*\n"
            "/investigate `<target>` — start an investigation\n"
            "/status `<id>` — check investigation status\n"
            "/results `<id>` — view detailed results\n"
            "/history — your recent investigations\n"
            "/help — show this help\n\n"
            "🔍 *Try it:* `/investigate github.com`"
        )
    else:
        text = (
            f"👁 Welcome to Argus OSINT, {name}!\n\n"
            "⚠️ Could not connect to the API. Please try again in a moment."
        )

    await message.answer(text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "👁 *Argus OSINT — Help*\n\n"
        "*Investigation targets:*\n"
        "• Domains: `example.com`\n"
        "• URLs: `https://example.com`\n"
        "• IP addresses: `192.168.1.1`\n\n"
        "*Commands:*\n"
        "`/investigate <target>` — Run full OSINT scan\n"
        "`/status <id>` — Check if investigation is done\n"
        "`/results <id>` — View full investigation report\n"
        "`/history` — Your last 10 investigations\n\n"
        "*Free plugins running on every scan:*\n"
        "🔍 WHOIS registration data\n"
        "🌐 DNS records (A, MX, NS, TXT…)\n"
        "🔐 Certificate transparency (subdomains)\n"
        "📍 IP geolocation & ASN info\n"
        "🌍 HTTP metadata (title, tech stack)\n\n"
        "_All data comes from free, public sources. No paid APIs required._"
    )
    await message.answer(text, parse_mode="Markdown")
