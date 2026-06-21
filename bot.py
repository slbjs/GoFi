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
            f"{human_readable_size(current)} / {human_readable_size(total)}"
        )
    except Exception:
        pass


async def get_best_server() -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.gofile.io/servers") as resp:
            data = await resp.json()
    if data.get("status") == "ok":
        return data["data"]["servers"][0]["name"]
    raise RuntimeError(f"Failed to get Gofile server: {data}")


async def upload_to_gofile(file_path: str, file_name: str) -> dict:
    server = await get_best_server()
    url = f"https://{server}.gofile.io/uploadFile"
    headers = {"Authorization": f"Bearer {GOFILE_API_KEY}"}
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            form = aiohttp.FormData()
            form.add_field("file", f, filename=file_name)
            async with session.post(url, data=form, headers=headers) as resp:
                result = await resp.json()
    if result.get("status") == "ok":
        return result["data"]
    raise RuntimeError(f"Gofile upload failed: {result}")


# ── Handlers ───────────────────────────────────────────────────────────────────

@app.on_message(filters.command("start") & filters.private)
async def start(_, message: Message):
    await message.reply_text(
        "👋 **Gofile Upload Bot**\n\n"
        "Send me any file and I'll upload it to [Gofile.io](https://gofile.io) "
        "and give you a shareable link.\n\n"
        "📤 Supported: Documents, Videos, Audio, Photos, Voice\n"
        "⚡ Max size: depends on your Telegram plan"
    )


@app.on_message(filters.command("help") & filters.private)
async def help_cmd(_, message: Message):
    await message.reply_text(
        "**How to use:**\n"
        "1. Send any file (document, video, audio, photo)\n"
        "2. Bot downloads it from Telegram\n"
        "3. Bot uploads it to Gofile\n"
        "4. You get a permanent share link 🔗\n\n"
        "**Commands:**\n"
        "/start – Welcome\n"
        "/help  – This message"
    )


@app.on_message(
    filters.private
    & (
        filters.document
        | filters.video
        | filters.audio
        | filters.photo
        | filters.animation
        | filters.voice
        | filters.video_note
    )
)
async def handle_file(_, message: Message):
    status = await message.reply_text("⏳ Starting...")

    media = (
        message.document
        or message.video
        or message.audio
        or message.photo
        or message.animation
        or message.voice
        or message.video_note
    )

    # Determine filename
    if hasattr(media, "file_name") and media.file_name:
        file_name = media.file_name
    elif message.photo:
        file_name = f"photo_{message.id}.jpg"
    elif message.voice:
        file_name = f"voice_{message.id}.ogg"
    elif message.video_note:
        file_name = f"videonote_{message.id}.mp4"
    else:
        ext = getattr(media, "mime_type", "application/octet-stream").split("/")[-1]
        file_name = f"file_{message.id}.{ext}"

    file_size = getattr(media, "file_size", 0)
    logger.info(f"Downloading: {file_name} ({human_readable_size(file_size)})")

    # Download from Telegram
    try:
        file_path = await message.download(
            progress=progress,
            progress_args=(status, "📥 Downloading")
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        file_path = await message.download()
    except Exception as e:
        await status.edit_text(f"❌ Download failed:\n`{e}`")
        return

    await status.edit_text("☁️ Uploading to Gofile...")

    # Upload to Gofile
    try:
        data = await upload_to_gofile(file_path, file_name)
    except Exception as e:
        await status.edit_text(f"❌ Upload failed:\n`{e}`")
        os.remove(file_path)
        return

    os.remove(file_path)

    link    = data.get("downloadPage", "N/A")
    file_id = data.get("fileId", "N/A")

    await status.edit_text(
        f"✅ **Upload Successful!**\n\n"
        f"📄 **File:** `{file_name}`\n"
        f"📦 **Size:** `{human_readable_size(file_size)}`\n"
        f"🔗 **Link:** {link}\n"
        f"🆔 **File ID:** `{file_id}`",
        disable_web_page_preview=True
    )
    logger.info(f"Uploaded: {file_name} → {link}")


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Bot starting...")
    app.run()
