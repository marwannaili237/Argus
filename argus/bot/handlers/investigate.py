from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import aiohttp
from config import get_settings
from bot.handlers.start import get_or_create_token

router = Router()
settings = get_settings()
API_BASE = f"http://localhost:{settings.api_port}/api/v1"


@router.message(Command("investigate"))
async def cmd_investigate(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(
            "❌ Please provide a target.\n\n"
            "*Usage:* `/investigate <target>`\n\n"
            "*Examples:*\n"
            "`/investigate github.com`\n"
            "`/investigate 8.8.8.8`\n"
            "`/investigate https://example.com`",
            parse_mode="Markdown",
        )
        return

    target = args[1].strip()

    token = await get_or_create_token(message)
    if not token:
        await message.answer("❌ Authentication failed. Please send /start and try again.")
        return

    status_msg = await message.answer(
        f"🔍 *Investigating:* `{target}`\n\n"
        "⏳ Running OSINT plugins…\n"
        "• WHOIS\n"
        "• DNS records\n"
        "• Certificate transparency\n"
        "• IP geolocation\n"
        "• HTTP metadata\n\n"
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
                        f"🔍 *Investigating:* `{target}`\n\n"
                        f"⏳ Investigation #{inv_id} is running…\n\n"
                        "• WHOIS ⏳\n"
                        "• DNS records ⏳\n"
                        "• Certificate transparency ⏳\n"
                        "• IP geolocation ⏳\n"
                        "• HTTP metadata ⏳\n\n"
                        f"_Check status: /status\\_{inv_id}_\n"
                        "_Results auto-update when done._",
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
        emoji = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(status, "❓")

        text = f"{emoji} *Investigation #{inv_id}*\n\nTarget: `{target}`\nStatus: *{status}*"
        if status == "completed":
            text += f"\n\nView results: /results\\_{inv_id}"

        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Error checking status: {e}")
