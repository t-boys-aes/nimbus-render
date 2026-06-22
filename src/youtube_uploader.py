import os
import json
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# Constants
OUTPUT_DIR = "output"
VIDEO_PATH = os.path.join(OUTPUT_DIR, "final_video.mp4")
THUMBNAIL_PATH = os.path.join(OUTPUT_DIR, "thumbnail.png")
SUBTITLES_PATH = os.path.join(OUTPUT_DIR, "final_subtitles.srt")
METADATA_PATH = os.path.join("temp", "youtube_metadata.json")

def get_youtube_client():
    """Retrieve an authenticated YouTube API client using refresh token configuration."""
    # Check if upload should be skipped
    skip_upload = os.environ.get("SKIP_YOUTUBE_UPLOAD", "False").lower() in ("true", "1", "yes")
    if skip_upload:
        logger.info(
            "SKIP_YOUTUBE_UPLOAD is enabled. Skipping real YouTube upload. (Simulated run)"
        )
        return None

    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if not client_id or not client_secret or not refresh_token:
        logger.warning(
            "YouTube credentials (client_id, client_secret, or refresh_token) are missing in environment variables. "
            "Skipping real YouTube upload. (Simulated run)"
        )
        return None

    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
        )
        youtube = build("youtube", "v3", credentials=creds)
        return youtube
    except Exception as e:
        logger.error(f"Failed to authenticate YouTube API client: {e}")
        return None

def upload_video():
    """Read metadata and upload video, custom thumbnail, and subtitles to YouTube."""
    if not os.path.exists(VIDEO_PATH):
        raise FileNotFoundError(f"Video file not found for upload at {VIDEO_PATH}")

    # Read Metadata
    title = "Default Title"
    description = "Default Description"
    tags = []
    
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
                title = meta.get("title", title)
                description = meta.get("description", description)
                tags = meta.get("tags", tags)
        except Exception as e:
            logger.error(f"Failed to read metadata file: {e}")
    else:
        logger.warning(f"Metadata file not found at {METADATA_PATH}. Using fallback defaults.")

    youtube = get_youtube_client()
    if not youtube:
        logger.info("--- SIMULATED UPLOAD SUCCESSFUL ---")
        logger.info(f"Video Path: {VIDEO_PATH}")
        logger.info(f"Title: {title}")
        logger.info(f"Description length: {len(description)} characters")
        logger.info(f"Tags: {tags}")
        if os.path.exists(THUMBNAIL_PATH):
            logger.info(f"Thumbnail: {THUMBNAIL_PATH}")
        if os.path.exists(SUBTITLES_PATH):
            logger.info(f"Subtitles: {SUBTITLES_PATH}")
        return "mock_video_id_12345"

    logger.info(f"Starting video upload for title: '{title}'...")
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "unlisted",  # Safe default to avoid instant public publishing before check
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        VIDEO_PATH,
        chunksize=1024*1024,
        resumable=True,
        mimetype="video/mp4"
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"Uploading video... {int(status.progress() * 100)}% completed.")

    video_id = response.get("id")
    logger.info(f"Video uploaded successfully! Video ID: {video_id}")

    # Upload Custom Thumbnail
    if os.path.exists(THUMBNAIL_PATH):
        try:
            logger.info(f"Uploading custom thumbnail from {THUMBNAIL_PATH}...")
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(THUMBNAIL_PATH, mimetype="image/png")
            ).execute()
            logger.info("Custom thumbnail uploaded successfully!")
        except Exception as e:
            logger.warning(f"Failed to upload custom thumbnail (channel might not be verified/phone-verified): {e}")

    # Upload Closed Captions (Subtitles)
    if os.path.exists(SUBTITLES_PATH):
        try:
            logger.info(f"Uploading subtitles from {SUBTITLES_PATH}...")
            body_caption = {
                "snippet": {
                    "videoId": video_id,
                    "language": "en",
                    "name": "English Auto-Subtitles",
                    "isDraft": False
                }
            }
            media_caption = MediaFileUpload(SUBTITLES_PATH, mimetype="*/*")
            youtube.captions().insert(
                part="snippet",
                body=body_caption,
                media_body=media_caption
            ).execute()
            logger.info("Closed captions uploaded successfully!")
        except Exception as e:
            logger.warning(f"Failed to upload closed captions (subtitles): {e}")

    logger.info(f"All upload tasks complete. YouTube Video Link: https://youtu.be/{video_id}")
    return video_id

if __name__ == "__main__":
    logger.info("Running standalone YouTube uploader...")
    try:
        upload_video()
    except Exception as e:
        logger.error(f"YouTube upload failed: {e}")
