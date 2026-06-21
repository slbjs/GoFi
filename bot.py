import os
import asyncio
import aiohttp
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG — edit these values
# ══════════════════════════════════════════════════════════════════════════════

API_ID         = 12345678                          # from https://my.telegram.org
API_HASH       = "your_api_hash_here"              # from https://my.telegram.org
BOT_TOKEN      = "your_bot_token_here"             # from @BotFather
GOFILE_API_KEY = "i4kO4vImcAHJDanHq5E8x2ZqA8eaQh8X"

# ══════════════════════════════════════════════════════════════════════════════

app = Client("gofile_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ── Helpers ────────────────────────────────────────────────────────────────────

def human_readable_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


async def progress(current: int, total: int, msg: Message, action: str):
    pct = current * 100 // total if total else 0
    filled = pct // 5
    bar = "█" * filled + "░" * (20 - filled)
    try:
        await msg.edit_text(
            f"**{action}**\n"
            f"`{bar}` {pct}%\n"
            f"{human
