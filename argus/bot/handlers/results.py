from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import aiohttp
from config import get_settings
from bot.handlers.start import get_or_create_token

router = Router()
settings = get_settings()
API_BASE = f"http://localhost:{settings.api_port}/api/v1"


@router.message(Command("results"))
async def cmd_results(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer(
            "❌ Please provide an investigation ID.\n\n*Usage:* `/results <id>`",
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
                    await message.answer("❌ Investigation not found.")
                    return
                data = await resp.json()

        status = data.get("status")
        if status == "running":
            await message.answer(f"⏳ Investigation #{inv_id} is still running. Check back soon!")
            return
        if status == "pending":
            await message.answer(f"⏳ Investigation #{inv_id} hasn't started yet.")
            return

        summary = data.get("summary")
        if summary:
            chunks = _chunk_text(summary, 4000)
            for chunk in chunks:
                await message.answer(chunk, parse_mode="Markdown")
        else:
            await message.answer(f"Investigation #{inv_id} completed but no data was collected.")

    except Exception as e:
        await message.answer(f"❌ Error fetching results: {e}")


@router.message(Command("history"))
async def cmd_history(message: Message):
    token = await get_or_create_token(message)
    if not token:
        await message.answer("❌ Authentication failed. Please send /start.")
        return

    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get(f"{API_BASE}/investigations?limit=10", headers=headers) as resp:
                investigations = await resp.json()

        if not investigations:
            await message.answer("You haven't run any investigations yet.\n\nTry: `/investigate github.com`", parse_mode="Markdown")
            return

        lines = ["📋 *Your Recent Investigations*\n"]
        status_emojis = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}

        for inv in investigations:
            emoji = status_emojis.get(inv.get("status", ""), "❓")
            lines.append(
                f"{emoji} *#{inv['id']}* `{inv['target']}`\n"
                f"   Type: {inv['target_type']} | {inv['status']}\n"
                f"   {inv['created_at'][:10]}"
            )

        lines.append("\n_Use /results\\_<id> to view details_")
        await message.answer("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        await message.answer(f"❌ Error fetching history: {e}")


def _chunk_text(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
