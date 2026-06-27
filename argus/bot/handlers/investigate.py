from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import aiohttp
from config import get_settings
from bot.handlers.start import get_or_create_token

router = Router()
settings = get_settings()
API_BASE = f"http://localhost:{settings.api_port}/api/v1"

TARGET_HELP = {
    "domain":   ("🌐", "WHOIS · DNS · Cert Transparency · IP Geo · HTTP"),
    "url":      ("🔗", "WHOIS · DNS · Cert Transparency · IP Geo · HTTP"),
    "ip":       ("🖥️", "IP Geolocation · Reverse DNS · ASN"),
    "email":    ("📧", "Breach DB · Email Rep · Gravatar · MX · GitHub"),
    "username": ("👤", "50+ platforms: GitHub · Twitter · Instagram · TikTok · Reddit…"),
    "phone":    ("📞", "Carrier · Country · Line Type · Timezone · Validity"),
    "image":    ("🖼️", "EXIF · GPS Coords · Camera Info · Reverse Search Links"),
    "unknown":  ("❓", "Best-effort scan"),
}


@router.message(Command("investigate"))
async def cmd_investigate(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(
            "❌ Please provide a target.\n\n"
            "*Supported targets:*\n"
            "🌐 `/investigate github.com` — domain\n"
            "🔗 `/investigate https://example.com` — URL\n"
            "🖥️ `/investigate 8.8.8.8` — IP address\n"
            "📧 `/investigate user@gmail.com` — email\n"
            "👤 `/investigate @username` — username (50+ sites)\n"
            "📞 `/investigate +14155552671` — phone number\n"
            "🖼️ `/investigate https://example.com/photo.jpg` — image EXIF",
            parse_mode="Markdown",
        )
        return

    target = args[1].strip()

    token = await get_or_create_token(message)
    if not token:
        await message.answer("❌ Authentication failed. Please send /start and try again.")
        return

    # Classify locally to show the right progress message
    from plugins.runner import classify_target
    target_type = classify_target(target)
    emoji, plugins_desc = TARGET_HELP.get(target_type, ("🔍", "OSINT scan"))

    status_msg = await message.answer(
        f"{emoji} *Investigating:* `{target}`\n\n"
        f"⏳ Running: {plugins_desc}\n\n"
        "_Results will appear here when complete._",
        parse_mode="Markdown",
    )

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "target": target,
                "telegram_chat_id": message.chat.id,
                "telegram_message_id": status_msg.message_id,
            }
            headers = {"Authorization": f"Bearer {token}"}
            async with session.post(f"{API_BASE}/investigations", json=payload, headers=headers) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    inv_id = data.get("id")
                    await status_msg.edit_text(
                        f"{emoji} *Investigating:* `{target}`\n\n"
                        f"⏳ *Investigation #{inv_id}* running…\n"
                        f"Plugins: {plugins_desc}\n\n"
                        f"_Check: /status\\_{inv_id} · Auto-updates when done_",
                        parse_mode="Markdown",
                    )
                else:
                    err = await resp.text()
                    await status_msg.edit_text(f"❌ Failed to start investigation: {err}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")


@router.message(Command("status"))
async def cmd_status(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer(
            "❌ Please provide an investigation ID.\n\n*Usage:* `/status <id>`",
            parse_mode="Markdown",
        )
        return

    inv_id = args[1].strip()
    token = await get_or_create_token(message)
    if not token:
        await message.answer("❌ Authentication failed. Please send /start.")
        return

    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get(f"{API_BASE}/investigations/{inv_id}", headers=headers) as resp:
                if resp.status == 404:
                    await message.answer("❌ Investigation not found or not yours.")
                    return
                data = await resp.json()

        status = data.get("status", "unknown")
        target = data.get("target", "?")
        target_type = data.get("target_type", "?")
        emoji, _ = TARGET_HELP.get(target_type, ("🔍", ""))
        status_emoji = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(status, "❓")

        text = (
            f"{status_emoji} *Investigation #{inv_id}*\n\n"
            f"{emoji} Target: `{target}` ({target_type})\n"
            f"Status: *{status}*"
        )
        if status == "completed":
            evidence_count = len(data.get("evidence", []))
            has_ai = any(e["plugin"] == "ai_analysis" for e in data.get("evidence", []))
            text += f"\nEvidence items: {evidence_count}"
            text += f"\n\n📄 /results\\_{inv_id}"
            if has_ai:
                text += f" | 🤖 /analyze\\_{inv_id}"

        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Error checking status: {e}")
