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
METADATA_PATH = os.path.join("temp", "youtube_metadata.json")

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

def get_or_create_spreadsheet(sheets, drive) -> str:
    """Get the spreadsheet ID from env or search/create 'Nimbus Render Production Log' in GSheets."""
    spreadsheet_id = os.environ.get("GSHEET_SPREADSHEET_ID")
    
    # If explicitly configured and not placeholder
    if spreadsheet_id and "your_gsheet" not in spreadsheet_id and spreadsheet_id.strip() != "":
        logger.info(f"Using configured Google Spreadsheet ID: {spreadsheet_id}")
        return spreadsheet_id

    logger.info("GSHEET_SPREADSHEET_ID not set. Checking if spreadsheet 'Nimbus Render Production Log' exists in Drive...")
    try:
        # Search for existing spreadsheet file
        query = "mimeType = 'application/vnd.google-apps.spreadsheet' and name = 'Nimbus Render Production Log' and trashed = false"
        results = drive.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            existing_id = items[0]['id']
            logger.info(f"Found existing Google Spreadsheet: '{items[0]['name']}' with ID: {existing_id}")
            return existing_id
            
        # Create new spreadsheet programmatically
        logger.info("Spreadsheet not found. Auto-creating Google Spreadsheet 'Nimbus Render Production Log'...")
        spreadsheet_body = {
            'properties': {
                'title': 'Nimbus Render Production Log'
            }
        }
        sheet_file = sheets.spreadsheets().create(body=spreadsheet_body, fields='spreadsheetId').execute()
        new_id = sheet_file.get('spreadsheetId')
        logger.info(f"Created spreadsheet successfully with ID: {new_id}")
        logger.info(f"👉 TIP: Salin spreadsheet ID ini ke berkas .env Anda: GSHEET_SPREADSHEET_ID={new_id}")
        
        # Initialize headers in Sheet1
        header_values = [["Date (Local)", "Video Title", "YouTube Link", "GDrive Link", "Status"]]
        body = {'values': header_values}
        sheets.spreadsheets().values().update(
            spreadsheetId=new_id,
            range="Sheet1!A1",
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        logger.info("Initialized spreadsheet columns: Date, Title, YouTube Link, GDrive Link, Status.")
        return new_id
    except Exception as e:
        logger.error(f"Failed to resolve or create Google Spreadsheet: {e}")
        raise e

def log_to_sheets(youtube_link: str = None, gdrive_link: str = None, status: str = "success"):
    """Log video metadata, YouTube link, and Google Drive link to Google Sheets."""
    # Read video title
    video_title = "Untitled_Video"
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
                video_title = meta.get("title", video_title)
        except Exception as e:
            logger.warning(f"Could not read metadata title for GSheets log: {e}")

    creds = get_google_credentials()
    if not creds:
        logger.info("--- SIMULATED GOOGLE SHEETS LOGGING SUCCESSFUL ---")
        logger.info(f"Log: [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] | Title: '{video_title}' | YT: {youtube_link} | Drive: {gdrive_link} | Status: {status}")
        return

    try:
        # Build API clients
        sheets = build("sheets", "v4", credentials=creds)
        drive = build("drive", "v3", credentials=creds)
        
        # Resolve target spreadsheet ID
        spreadsheet_id = get_or_create_spreadsheet(sheets, drive)
        
        # Append log data row
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_row = [[
            date_str,
            video_title,
            youtube_link or "N/A",
            gdrive_link or "N/A",
            status.upper()
        ]]
        
        body = {'values': log_row}
        sheets.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A:E",
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
        log_to_sheets(youtube_link="https://youtu.be/mock_id", gdrive_link="https://drive.google.com/mock_file", status="success")
    except Exception as e:
        logger.error(f"Google Sheets test failed: {e}")
