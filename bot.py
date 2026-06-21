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

API_ID         = 29025963
API_HASH       = "c6e5ae97263b00062c72f13649f325a4"
BOT_TOKEN      = "7861537839:AAF7acuDMLkz-hoz4shl6j6jUbd5EOukQwg"
GOFILE_API_KEY = "i4kO4vImcAHJDanHq5E8x2ZqA8eaQh8X"

app = Client("gofile_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def human_readable_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return str(round(size, 2)) + " " + unit
        size /= 1024
    return str(round(size, 2)) + " PB"

async def progress(current, total, msg, action):
    pct = current * 100 // total if total else 0
    filled = pct // 5
    bar = "█" * filled + "░" * (20 - filled)
    text = "**" + action + "**\n`" + bar + "` " + str(pct) + "%\n" + human_readable_size(current) + " / " + human_readable_size(total)
    try:
        await msg.edit_text(text)
    except Exception:
        pass

async def get_best_server():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.gofile.io/servers") as resp:
            data = await resp.json()
    if data.get("status") == "ok":
        return data["data"]["servers"][0]["name"]
    raise RuntimeError("Failed to get Gofile server: " + str(data))

async def upload_to_gofile(file_path, file_name):
    server = await get_best_server()
    url = "https://" + server + ".gofile.io/contents/uploadfile"
    headers = {"Authorization": "Bearer " + GOFILE_API_KEY}
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            form = aiohttp.FormData()
            form.add_field("file", f, filename=file_name)
            async with session.post(url, data=form, headers=headers) as resp:
                result = await resp.json()
    if result.get("status") == "ok":
        return result["data"]
    raise RuntimeError("Gofile upload failed: " + str(result))

async def create_direct_link(file_id):
    url = "https://api.gofile.io/contents/" + file_id + "/directlinks"
    headers = {"Authorization": "Bearer " + GOFILE_API_KEY, "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={}, headers=headers) as resp:
            result = await resp.json()
    if result.get("status") == "ok":
        return result["data"].get("url", "N/A")
    return "N/A"

@app.on_message(filters.command("start") & filters.private)
async def start(_, message):
    await message.reply_text(
        "👋 **Gofile Upload Bot**\n\n"
        "Send me any file and I will upload it to Gofile.io and give you a shareable link.\n\n"
        "📤 Supported: Documents, Videos, Audio, Photos, Voice"
    )

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(_, message):
    await message.reply_text(
        "**How to use:**\n"
        "1. Send any file\n"
        "2. Bot downloads from Telegram\n"
        "3. Bot uploads to Gofile\n"
        "4. You get a share link\n\n"
        "**Commands:**\n"
        "/start - Welcome\n"
        "/help - This message"
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
async def handle_file(_, message):
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

    if hasattr(media, "file_name") and media.file_name:
        file_name = media.file_name
    elif message.photo:
        file_name = "photo_" + str(message.id) + ".jpg"
    elif message.voice:
        file_name = "voice_" + str(message.id) + ".ogg"
    elif message.video_note:
        file_name = "videonote_" + str(message.id) + ".mp4"
    else:
        ext = getattr(media, "mime_type", "application/octet-stream").split("/")[-1]
        file_name = "file_" + str(message.id) + "." + ext

    file_size = getattr(media, "file_size", 0)

    try:
        file_path = await message.download(
            progress=progress,
            progress_args=(status, "📥 Downloading")
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        file_path = await message.download()
    except Exception as e:
        await status.edit_text("❌ Download failed:\n" + str(e))
        return

    await status.edit_text("☁️ Uploading to Gofile...")

    try:
        data = await upload_to_gofile(file_path, file_name)
    except Exception as e:
        await status.edit_text("❌ Upload failed:\n" + str(e))
        os.remove(file_path)
        return

    os.remove(file_path)

    file_id   = data.get("fileId", "")
    page_link = data.get("downloadPage", "N/A")

    await status.edit_text("🔗 Getting direct link...")

    direct_link = await create_direct_link(file_id) if file_id else "N/A"

    await status.edit_text(
        "✅ **Upload Successful!**\n\n"
        "📄 **File:** " + file_name + "\n"
        "📦 **Size:** " + human_readable_size(file_size) + "\n"
        "🔗 **Page:** " + page_link + "\n"
        "⬇️ **Direct:** " + direct_link + "\n"
        "🆔 **File ID:** " + file_id,
        disable_web_page_preview=True
    )

if __name__ == "__main__":
    logger.info("Bot starting...")
    app.run()
