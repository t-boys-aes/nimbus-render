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
TEMP_DIR = "temp"
OUTPUT_DIR = "output"
VIDEO_PATH = os.path.join(OUTPUT_DIR, "final_video.mp4")
METADATA_PATH = os.path.join(TEMP_DIR, "youtube_metadata.json")

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
    
    # Create multi-level subtitles folder: Subtitles -> en
    subtitles_root_id = get_or_create_subfolder(drive, "Subtitles", root_id)
    subfolders["subtitles_en"] = get_or_create_subfolder(drive, "en", subtitles_root_id)
    
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

def upload_to_drive() -> dict:
    """Upload final video, thumbnail, subtitles, and production package to Google Drive.
    Returns a dictionary containing the web shareable links for all uploaded files."""
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

    # Paths of files to upload
    thumbnail_path = os.path.join(OUTPUT_DIR, "thumbnail.png")
    subtitles_path = os.path.join(OUTPUT_DIR, "final_subtitles.srt")
    
    # 1. Compile consolidated production package json
    package_path = os.path.join(TEMP_DIR, "production_package.json")
    package_data = {}
    
    script_data_path = os.path.join(TEMP_DIR, "script_data.json")
    news_data_path = os.path.join(TEMP_DIR, "news_data.json")
    attributions_path = os.path.join(TEMP_DIR, "footage_attributions.json")
    
    if os.path.exists(news_data_path):
        try:
            with open(news_data_path, "r", encoding="utf-8") as f:
                package_data["news"] = json.load(f)
        except Exception as e:
            logger.warning(f"Could not include news in package: {e}")
            
    if os.path.exists(script_data_path):
        try:
            with open(script_data_path, "r", encoding="utf-8") as f:
                package_data["script"] = json.load(f)
        except Exception as e:
            logger.warning(f"Could not include script in package: {e}")
            
    if os.path.exists(attributions_path):
        try:
            with open(attributions_path, "r", encoding="utf-8") as f:
                package_data["footage_attributions"] = json.load(f)
        except Exception as e:
            logger.warning(f"Could not include footage attributions in package: {e}")
            
    # Write package file
    if package_data:
        try:
            with open(package_path, "w", encoding="utf-8") as f:
                json.dump(package_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not write production package file: {e}")

    drive = get_drive_client()
    if not drive:
        logger.info("--- SIMULATED GOOGLE DRIVE UPLOAD SUCCESSFUL ---")
        mock_video_link = f"https://drive.google.com/file/d/mock_gdrive_video_id_12345/view?usp=drivesdk"
        mock_thumb_link = f"https://drive.google.com/file/d/mock_gdrive_thumb_id_12345/view?usp=drivesdk"
        mock_script_link = f"https://drive.google.com/file/d/mock_gdrive_script_id_12345/view?usp=drivesdk"
        mock_srt_link = f"https://drive.google.com/file/d/mock_gdrive_srt_id_12345/view?usp=drivesdk"
        
        logger.info(f"Simulated Upload Files under 'The Strategic Brief':")
        logger.info(f"  - Full Videos: {base_name}.mp4 -> {mock_video_link}")
        logger.info(f"  - Thumbnails: {base_name}.png -> {mock_thumb_link}")
        logger.info(f"  - Metadata: {base_name}_package.json -> {mock_script_link}")
        logger.info(f"  - Subtitles (en): {base_name}.srt -> {mock_srt_link}")
        
        return {
            "video": mock_video_link,
            "thumbnail": mock_thumb_link,
            "script": mock_script_link,
            "srt": mock_srt_link
        }

    try:
        # Resolve target folder structure
        subfolders = get_or_create_folder_structure(drive)
        
        links = {
            "video": "",
            "thumbnail": "",
            "script": "",
            "srt": ""
        }

        # 1. Upload Video to 'Full Videos'
        video_filename = f"{base_name}.mp4"
        links["video"] = upload_file_to_drive(
            drive, 
            local_path=VIDEO_PATH, 
            dest_filename=video_filename, 
            folder_id=subfolders["videos"], 
            mimetype="video/mp4"
        )

        # 2. Upload Thumbnail to 'Thumbnails'
        if os.path.exists(thumbnail_path):
            thumbnail_filename = f"{base_name}.png"
            links["thumbnail"] = upload_file_to_drive(
                drive, 
                local_path=thumbnail_path, 
                dest_filename=thumbnail_filename, 
                folder_id=subfolders["thumbnails"], 
                mimetype="image/png"
            )

        # 3. Upload Consolidated Production Package JSON to 'Metadata'
        if os.path.exists(package_path):
            package_filename = f"{base_name}_package.json"
            links["script"] = upload_file_to_drive(
                drive, 
                local_path=package_path, 
                dest_filename=package_filename, 
                folder_id=subfolders["metadata"], 
                mimetype="application/json"
            )

        # 4. Upload Subtitles to 'Subtitles/en'
        if os.path.exists(subtitles_path):
            srt_filename = f"{base_name}.srt"
            links["srt"] = upload_file_to_drive(
                drive, 
                local_path=subtitles_path, 
                dest_filename=srt_filename, 
                folder_id=subfolders["subtitles_en"], 
                mimetype="text/plain"
            )

        logger.info("All files successfully uploaded to Google Drive folder structure!")
        return links

    except Exception as e:
        logger.error(f"Google Drive upload process failed: {e}")
        raise e

if __name__ == "__main__":
    logger.info("Running standalone Google Drive storage test...")
    try:
        upload_to_drive()
    except Exception as e:
        logger.error(f"Google Drive test failed: {e}")
