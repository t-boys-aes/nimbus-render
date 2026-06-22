import os
import json
import logging
from datetime import datetime
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
METADATA_PATH = os.path.join("temp", "youtube_metadata.json")

def get_drive_client():
    """Retrieve an authenticated Google Drive API client using shared/dedicated OAuth2 configuration."""
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN") or os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if not client_id or not client_secret or not refresh_token:
        logger.warning("OAuth2 credentials missing in environment. Google Drive storage will be simulated.")
        return None

    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        drive = build("drive", "v3", credentials=creds)
        return drive
    except Exception as e:
        logger.error(f"Failed to authenticate Google Drive API client: {e}")
        return None

def get_or_create_subfolder(drive, folder_name: str, parent_id: str = None) -> str:
    """Search for a subfolder by name under a parent folder, or create it if it doesn't exist."""
    query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    try:
        results = drive.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            return items[0]['id']
        
        # Create it if not found
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        folder = drive.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
        logger.info(f"Created subfolder '{folder_name}' with ID: {folder_id}")
        return folder_id
    except Exception as e:
        logger.error(f"Failed to resolve or create Google Drive subfolder '{folder_name}': {e}")
        raise e

def get_or_create_folder_structure(drive) -> dict:
    """Resolve the root 'The Strategic Brief' folder and its standard subfolders."""
    root_id = os.environ.get("GDRIVE_FOLDER_ID")
    
    # If root folder ID is not configured, create or find "The Strategic Brief"
    if not root_id or "your_gdrive" in root_id or root_id.strip() == "":
        root_id = get_or_create_subfolder(drive, "The Strategic Brief")
        logger.info(f"Root Google Drive folder resolved to: 'The Strategic Brief' (ID: {root_id})")
        logger.info(f"👉 TIP: Salin folder ID ini ke berkas .env Anda: GDRIVE_FOLDER_ID={root_id}")
    
    # Resolve subfolders
    subfolders = {
        "videos": get_or_create_subfolder(drive, "Full Videos", root_id),
        "thumbnails": get_or_create_subfolder(drive, "Thumbnails", root_id),
        "metadata": get_or_create_subfolder(drive, "Metadata", root_id),
        "shorts": get_or_create_subfolder(drive, "Shorts & Reels", root_id)
    }
    
    return subfolders

def upload_file_to_drive(drive, local_path: str, dest_filename: str, folder_id: str, mimetype: str) -> str:
    """Upload a single file to a specific Drive folder and make it readable by anyone with the link."""
    if not os.path.exists(local_path):
        logger.warning(f"File not found for upload: {local_path}")
        return ""
        
    try:
        file_metadata = {
            'name': dest_filename,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(
            local_path,
            mimetype=mimetype,
            resumable=True,
            chunksize=1024*1024
        )
        
        request = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Uploading {dest_filename} to Google Drive... {int(status.progress() * 100)}% completed.")
        
        file_id = response.get('id')
        web_link = response.get('webViewLink')
        
        # Make the file readable by anyone with link (so you can view it directly)
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader',
                'allowFileDiscovery': False
            }
            drive.permissions().create(fileId=file_id, body=permission).execute()
        except Exception as perm_err:
            logger.warning(f"Could not change file sharing permissions for {dest_filename}: {perm_err}")
            
        return web_link
    except Exception as e:
        logger.error(f"Failed to upload {dest_filename} to Google Drive: {e}")
        raise e

def upload_to_drive() -> str:
    """Upload final video, thumbnail, and metadata to their respective subfolders in Google Drive.
    Returns the web shareable link of the final video."""
    if not os.path.exists(VIDEO_PATH):
        raise FileNotFoundError(f"Video file not found at {VIDEO_PATH} for Google Drive upload.")

    # Read video title to name the files cleanly
    video_title = "Untitled_Video"
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
                video_title = meta.get("title", video_title)
        except Exception as e:
            logger.warning(f"Could not read metadata title: {e}")

    # Standardize filename prefixes: YYYYMMDD_Clean_Title
    date_str = datetime.now().strftime("%Y%m%d")
    clean_title = "".join([c if c.isalnum() else "_" for c in video_title]).strip("_")
    while "__" in clean_title:
        clean_title = clean_title.replace("__", "_")
    base_name = f"{date_str}_{clean_title[:50]}"

    drive = get_drive_client()
    if not drive:
        logger.info("--- SIMULATED GOOGLE DRIVE UPLOAD SUCCESSFUL ---")
        mock_video_link = f"https://drive.google.com/file/d/mock_gdrive_video_id_12345/view?usp=drivesdk"
        logger.info(f"Simulated Upload Files under 'The Strategic Brief':")
        logger.info(f"  - Full Videos: {base_name}.mp4 -> {mock_video_link}")
        logger.info(f"  - Thumbnails: {base_name}.png -> (simulated)")
        logger.info(f"  - Metadata: {base_name}.json -> (simulated)")
        return mock_video_link

    try:
        # Resolve target folder structure
        subfolders = get_or_create_folder_structure(drive)

        # 1. Upload Video to 'Full Videos'
        video_filename = f"{base_name}.mp4"
        video_link = upload_file_to_drive(
            drive, 
            local_path=VIDEO_PATH, 
            dest_filename=video_filename, 
            folder_id=subfolders["videos"], 
            mimetype="video/mp4"
        )
        logger.info(f"Uploaded Video successfully: {video_link}")

        # 2. Upload Thumbnail to 'Thumbnails'
        THUMBNAIL_PATH = os.path.join(OUTPUT_DIR, "thumbnail.png")
        if os.path.exists(THUMBNAIL_PATH):
            thumbnail_filename = f"{base_name}.png"
            upload_file_to_drive(
                drive, 
                local_path=THUMBNAIL_PATH, 
                dest_filename=thumbnail_filename, 
                folder_id=subfolders["thumbnails"], 
                mimetype="image/png"
            )
            logger.info("Uploaded Thumbnail successfully.")

        # 3. Upload Metadata JSON to 'Metadata'
        if os.path.exists(METADATA_PATH):
            meta_filename = f"{base_name}.json"
            upload_file_to_drive(
                drive, 
                local_path=METADATA_PATH, 
                dest_filename=meta_filename, 
                folder_id=subfolders["metadata"], 
                mimetype="application/json"
            )
            logger.info("Uploaded Metadata JSON successfully.")

        return video_link

    except Exception as e:
        logger.error(f"Google Drive upload process failed: {e}")
        raise e

if __name__ == "__main__":
    logger.info("Running standalone Google Drive storage test...")
    try:
        upload_to_drive()
    except Exception as e:
        logger.error(f"Google Drive test failed: {e}")
