import os
import json
import logging
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# Constants
TEMP_DIR = "temp"
METADATA_PATH = os.path.join(TEMP_DIR, "youtube_metadata.json")

HEADERS = [
    "Date Created (Local)",
    "Date Published (YouTube)",
    "Video Title",
    "Type",
    "Caption / Description",
    "YouTube Link",
    "Video Link (Drive)",
    "Thumbnail Link (Drive)",
    "Script Link (Drive)",
    "SRT Link (Drive)",
    "Status"
]

def get_google_credentials():
    """Retrieve shared Google Credentials."""
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN") or os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if not client_id or not client_secret or not refresh_token:
        return None
        
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
    )

def get_or_create_root_folder_id(drive) -> str:
    """Resolve the root folder ID for 'The Strategic Brief'."""
    root_id = os.environ.get("GDRIVE_FOLDER_ID")
    if root_id and "your_gdrive" not in root_id and root_id.strip() != "":
        return root_id
    
    # Search for it
    query = "mimeType = 'application/vnd.google-apps.folder' and name = 'The Strategic Brief' and trashed = false"
    try:
        results = drive.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']
            
        # Create it if not found
        file_metadata = {
            'name': 'The Strategic Brief',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive.files().create(body=file_metadata, fields='id').execute()
        new_id = folder.get('id')
        logger.info(f"Created root folder 'The Strategic Brief' with ID: {new_id}")
        return new_id
    except Exception as e:
        logger.error(f"Failed to resolve root folder ID: {e}")
        raise e

def get_or_create_spreadsheet(sheets, drive) -> str:
    """Get the spreadsheet ID from env or search/create 'Nimbus Render Production Log' inside root folder."""
    spreadsheet_id = os.environ.get("GSHEET_SPREADSHEET_ID")
    
    # If explicitly configured and not placeholder
    if spreadsheet_id and "your_gsheet" not in spreadsheet_id and spreadsheet_id.strip() != "":
        logger.info(f"Using configured Google Spreadsheet ID: {spreadsheet_id}")
        
        # Ensure headers are correct
        try:
            sheets.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range="Sheet1!A1:K1",
                valueInputOption="USER_ENTERED",
                body={'values': [HEADERS]}
            ).execute()
        except Exception as e:
            logger.warning(f"Could not verify or update headers in existing spreadsheet: {e}")
            
        return spreadsheet_id

    try:
        root_id = get_or_create_root_folder_id(drive)
        
        # Search for existing spreadsheet file inside root folder
        query = f"mimeType = 'application/vnd.google-apps.spreadsheet' and name = 'Nimbus Render Production Log' and '{root_id}' in parents and trashed = false"
        results = drive.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            existing_id = items[0]['id']
            logger.info(f"Found existing Google Spreadsheet in root folder: '{items[0]['name']}' with ID: {existing_id}")
            # Ensure headers are set
            sheets.spreadsheets().values().update(
                spreadsheetId=existing_id,
                range="Sheet1!A1:K1",
                valueInputOption="USER_ENTERED",
                body={'values': [HEADERS]}
            ).execute()
            return existing_id
            
        # Create new spreadsheet inside root folder
        logger.info("Spreadsheet not found. Auto-creating Google Spreadsheet 'Nimbus Render Production Log' inside 'The Strategic Brief'...")
        
        spreadsheet_metadata = {
            'name': 'Nimbus Render Production Log',
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [root_id]
        }
        
        sheet_file = drive.files().create(body=spreadsheet_metadata, fields='id').execute()
        new_id = sheet_file.get('id')
        logger.info(f"Created spreadsheet successfully with ID: {new_id}")
        logger.info(f"👉 TIP: Salin spreadsheet ID ini ke berkas .env Anda: GSHEET_SPREADSHEET_ID={new_id}")
        
        # Initialize headers in Sheet1
        sheets.spreadsheets().values().update(
            spreadsheetId=new_id,
            range="Sheet1!A1:K1",
            valueInputOption="USER_ENTERED",
            body={'values': [HEADERS]}
        ).execute()
        logger.info("Initialized spreadsheet columns.")
        return new_id
    except Exception as e:
        logger.error(f"Failed to resolve or create Google Spreadsheet: {e}")
        raise e

def log_to_sheets(youtube_link: str = None, gdrive_links: dict = None, status: str = "success"):
    """Log video metadata, YouTube link, and all Google Drive links to Google Sheets."""
    # Read video metadata
    video_title = "Untitled_Video"
    video_description = ""
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
                video_title = meta.get("title", video_title)
                video_description = meta.get("description", "")
        except Exception as e:
            logger.warning(f"Could not read metadata for GSheets log: {e}")

    # Fallback for older calls passing single string
    if isinstance(gdrive_links, str):
        gdrive_links = {"video": gdrive_links}
    elif gdrive_links is None:
        # Try loading from JSON
        links_json_path = os.path.join(TEMP_DIR, "gdrive_links.json")
        if os.path.exists(links_json_path):
            try:
                with open(links_json_path, "r") as f:
                    gdrive_links = json.load(f)
            except:
                gdrive_links = {}
        else:
            gdrive_links = {}

    creds = get_google_credentials()
    if not creds:
        logger.info("--- SIMULATED GOOGLE SHEETS LOGGING SUCCESSFUL ---")
        logger.info(f"Log: [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] | Title: '{video_title}' | Status: {status}")
        logger.info(f"  - YouTube: {youtube_link}")
        logger.info(f"  - Drive Links: {gdrive_links}")
        return

    try:
        # Build API clients
        sheets = build("sheets", "v4", credentials=creds)
        drive = build("drive", "v3", credentials=creds)
        
        # Resolve target spreadsheet ID
        spreadsheet_id = get_or_create_spreadsheet(sheets, drive)
        
        # Append log data row
        date_created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Date Published is YouTube upload time or N/A
        date_published = "N/A"
        if youtube_link and youtube_link != "N/A" and "mock" not in youtube_link:
            date_published = date_created
            
        log_row = [[
            date_created,
            date_published,
            video_title,
            "Full Video",
            video_description,
            youtube_link or "N/A",
            gdrive_links.get("video") or "N/A",
            gdrive_links.get("thumbnail") or "N/A",
            gdrive_links.get("script") or "N/A",
            gdrive_links.get("srt") or "N/A",
            status.upper()
        ]]
        
        body = {'values': log_row}
        sheets.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A:K",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        logger.info(f"Production successfully logged to GSheets (Spreadsheet ID: {spreadsheet_id})!")
    except Exception as e:
        logger.error(f"Google Sheets logging failed: {e}")
        raise e

if __name__ == "__main__":
    logger.info("Running standalone Google Sheets logger test...")
    try:
        log_to_sheets(
            youtube_link="https://youtu.be/mock_id", 
            gdrive_links={
                "video": "https://drive.google.com/video",
                "thumbnail": "https://drive.google.com/thumb",
                "script": "https://drive.google.com/script",
                "srt": "https://drive.google.com/srt"
            }, 
            status="success"
        )
    except Exception as e:
        logger.error(f"Google Sheets test failed: {e}")
