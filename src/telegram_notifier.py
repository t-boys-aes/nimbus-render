import os
import logging
import requests
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

def send_telegram_message(message: str) -> bool:
    """Send raw HTML-formatted message to Telegram channel/chat via bot API."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id or "your_telegram" in bot_token:
        logger.warning("Telegram Bot Credentials missing or unconfigured. Notification will be skipped.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        res_data = response.json()
        if res_data.get("ok"):
            logger.info("Telegram notification sent successfully!")
            return True
        else:
            logger.error(f"Telegram API responded with error: {res_data}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

def notify_pipeline_status(
    pipeline_state: dict,
    video_title: str = "",
    article_url: str = "",
    youtube_link: str = "",
    gdrive_link: str = "",
    error_message: str = ""
):
    """Format and send a structured run report including status for each phase."""
    emoji_success = "✅"
    emoji_failed = "❌"
    emoji_pending = "⏳"
    
    # Translate status to visual emojis
    def get_status_emoji(step_name):
        state = pipeline_state.get(step_name, "pending")
        if state == "success":
            return f"{emoji_success} Success"
        elif state == "failed":
            return f"{emoji_failed} Failed"
        else:
            return f"{emoji_pending} Skipped"

    # Title fallback
    title_display = video_title if video_title else "New Geopolitical Video Draft"
    article_display = f"<a href='{article_url}'>Link Artikel</a>" if article_url else "N/A"
    
    yt_display = f"<a href='{youtube_link}'>{youtube_link}</a>" if youtube_link and "mock" not in youtube_link else "N/A"
    drive_display = f"<a href='{gdrive_link}'>Buka di Google Drive</a>" if gdrive_link and "mock" not in gdrive_link else "N/A"

    # Construct status list
    steps_list = []
    # Core pipeline steps order
    core_steps = ["assets", "news", "script", "tts", "footage", "render", "thumbnail", "metadata", "drive", "sheets", "upload"]
    for step in core_steps:
        # Capitalize and format step name
        name_formatted = step.capitalize()
        if step == "tts":
            name_formatted = "TTS Voiceover"
        elif step == "upload":
            name_formatted = "YouTube Upload"
        elif step == "drive":
            name_formatted = "GDrive Backup"
        elif step == "sheets":
            name_formatted = "Sheets Log"
            
        steps_list.append(f"• <b>{name_formatted}</b>: {get_status_emoji(step)}")

    steps_text = "\n".join(steps_list)

    # Determine overall status banner
    is_success = all(state == "success" for step, state in pipeline_state.items() if step in ["assets", "news", "script", "tts", "footage", "render", "thumbnail", "metadata"])
    status_banner = "🚀 <b>NIMBUS PIPELINE RUN SUCCESSFUL</b>" if is_success else "⚠️ <b>NIMBUS PIPELINE RUN FAILED</b>"

    # Construct the final HTML message body
    msg_blocks = [
        status_banner,
        "==================================",
        f"👤 <b>Topik Video</b>: {title_display}",
        f"📰 <b>Sumber Berita</b>: {article_display}",
        "==================================",
        "📊 <b>Status Tahapan</b>:",
        steps_text,
        "==================================",
        "🔗 <b>Tautan Video</b>:",
        f"🎥 YouTube: {yt_display}",
        f"📁 Google Drive: {drive_display}"
    ]

    # Append error details if failure occurred
    if error_message:
        msg_blocks.append("==================================")
        msg_blocks.append(f"🚨 <b>Pesan Error</b>:\n<code>{error_message}</code>")

    final_msg = "\n".join(msg_blocks)
    send_telegram_message(final_msg)

if __name__ == "__main__":
    logger.info("Running standalone Telegram notifier test...")
    mock_state = {
        "assets": "success",
        "news": "success",
        "script": "success",
        "tts": "success",
        "footage": "success",
        "render": "success",
        "thumbnail": "success",
        "metadata": "success",
        "drive": "success",
        "sheets": "success",
        "upload": "failed"
    }
    notify_pipeline_status(
        mock_state,
        video_title="How a New U.S. Deal Could Reconnect Iran",
        article_url="https://example.com/iran-news",
        youtube_link="https://youtu.be/mock_id",
        gdrive_link="https://drive.google.com/mock",
        error_message="YouTube API quota exceeded: 403 Forbidden"
    )
