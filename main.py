import os
import json
import argparse
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# State Configuration
TEMP_DIR = "temp"
STATE_FILE = os.path.join(TEMP_DIR, "state.json")

# Import pipeline modules
from src.asset_downloader import setup_assets
from src.news_sourcer import source_news
from src.script_generator import generate_script
from src.tts_generator import run_tts
from src.footage_fetcher import fetch_all_footage
from src.video_renderer import build_video_segments
from src.thumbnail_generator import generate_thumbnail
from src.metadata_generator import generate_youtube_metadata
from src.youtube_uploader import upload_video
from src.drive_storage import upload_to_drive
from src.sheets_logger import log_to_sheets
from src.telegram_notifier import notify_pipeline_status

# Define ordered pipeline steps
PIPELINE_STEPS = ["assets", "news", "script", "tts", "footage", "render", "thumbnail", "metadata", "drive", "sheets", "upload"]

def load_state() -> dict:
    """Load the pipeline progress state from temp/state.json."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read state file: {e}. Resetting state.")
    
    # Return default empty state
    return {step: "pending" for step in PIPELINE_STEPS}

def save_state(state: dict):
    """Save the pipeline progress state to temp/state.json."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to write state file: {e}")

def run_step(step_name: str, url_override: str = None) -> bool:
    """Execute a single pipeline step and handle its function call."""
    logger.info(f"==================================================")
    logger.info(f" RUNNING PIPELINE STEP: {step_name.upper()}")
    logger.info(f"==================================================")
    
    try:
        if step_name == "assets":
            setup_assets()
        elif step_name == "news":
            source_news(override_url=url_override)
        elif step_name == "script":
            generate_script()
        elif step_name == "tts":
            run_tts()
        elif step_name == "footage":
            fetch_all_footage()
        elif step_name == "render":
            build_video_segments()
        elif step_name == "thumbnail":
            generate_thumbnail()
        elif step_name == "metadata":
            generate_youtube_metadata()
        elif step_name == "upload":
            video_id = upload_video()
            youtube_link = f"https://youtu.be/{video_id}"
            with open(os.path.join(TEMP_DIR, "youtube_link.txt"), "w") as f:
                f.write(youtube_link)
        elif step_name == "drive":
            gdrive_links = upload_to_drive()
            with open(os.path.join(TEMP_DIR, "gdrive_links.json"), "w") as f:
                json.dump(gdrive_links, f, indent=4)
            # Write fallback link for backwards compatibility
            with open(os.path.join(TEMP_DIR, "gdrive_link.txt"), "w") as f:
                f.write(gdrive_links.get("video", ""))
        elif step_name == "sheets":
            gdrive_links = None
            gdrive_links_path = os.path.join(TEMP_DIR, "gdrive_links.json")
            if os.path.exists(gdrive_links_path):
                with open(gdrive_links_path, "r") as f:
                    gdrive_links = json.load(f)
                    
            youtube_link = ""
            youtube_link_path = os.path.join(TEMP_DIR, "youtube_link.txt")
            if os.path.exists(youtube_link_path):
                with open(youtube_link_path, "r") as f:
                    youtube_link = f.read().strip()
                    
            log_to_sheets(youtube_link=youtube_link, gdrive_links=gdrive_links, status="success")
            
        logger.info(f"STEP SUCCESS: {step_name.upper()}")
        return True
    except Exception as e:
        logger.error(f"STEP FAILED: {step_name.upper()} - Error: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(description="Nimbus Render YouTube Automation Pipeline Orchestrator")
    parser.add_argument("--resume", action="store_true", help="Resume from the last failed step")
    parser.add_argument("--force", action="store_true", help="Force run all steps from scratch")
    parser.add_argument("--step", type=str, choices=PIPELINE_STEPS, help="Run only a specific single step")
    parser.add_argument("--url", type=str, help="Manually override news sourcing with this specific article URL")
    parser.add_argument("--render-only", action="store_true", help="Run only rendering steps (assets to drive)")
    parser.add_argument("--upload-only", action="store_true", help="Run only uploading steps (upload and sheets)")
    
    args = parser.parse_args()
    
    state = load_state()
    
    gdrive_link_path = os.path.join(TEMP_DIR, "gdrive_link.txt")
    youtube_link_path = os.path.join(TEMP_DIR, "youtube_link.txt")
    
    # Define steps to run based on modes
    steps_to_run = PIPELINE_STEPS
    if args.render_only:
        steps_to_run = ["assets", "news", "script", "tts", "footage", "render", "thumbnail", "metadata", "drive"]
    elif args.upload_only:
        steps_to_run = ["upload", "sheets"]
        
    # 1. Run single step override
    if args.step:
        logger.info(f"Single step manual execution triggered for: '{args.step}'")
        success = run_step(args.step, url_override=args.url)
        state[args.step] = "success" if success else "failed"
        save_state(state)
        if not success:
            sys.exit(1)
        sys.exit(0)
        
    # 2. Force execution from scratch
    if args.force:
        logger.info("Force flag set. Resetting pipeline state and running all steps.")
        state = {step: "pending" for step in PIPELINE_STEPS}
        save_state(state)
        # Clear link files
        for p in [gdrive_link_path, youtube_link_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass
        
    # 3. Main pipeline loop wrapped in error handling for notifications
    error_occurred = False
    error_msg = ""
    
    try:
        for step in steps_to_run:
            # If resuming and step was already successful, skip it
            if args.resume and state.get(step) == "success":
                logger.info(f"Skipping already completed step: {step.upper()}")
                continue
                
            success = run_step(step, url_override=args.url)
            state[step] = "success" if success else "failed"
            save_state(state)
            
            if not success:
                error_occurred = True
                error_msg = f"Pipeline execution halted at step '{step.upper()}'."
                break
    except Exception as e:
        error_occurred = True
        error_msg = str(e)
        logger.error(f"Pipeline crashed with exception: {e}", exc_info=True)
        
    # Read metadata values for notification
    video_title = "Untitled Nimbus Video"
    article_url = ""
    metadata_path = os.path.join(TEMP_DIR, "youtube_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                video_title = meta.get("title", video_title)
        except:
            pass
            
    news_data_path = os.path.join(TEMP_DIR, "news_data.json")
    if os.path.exists(news_data_path):
        try:
            with open(news_data_path, "r", encoding="utf-8") as f:
                news = json.load(f)
                article_url = news.get("url", "")
        except:
            pass
            
    # Read links
    gdrive_links = None
    gdrive_links_path = os.path.join(TEMP_DIR, "gdrive_links.json")
    if os.path.exists(gdrive_links_path):
        try:
            with open(gdrive_links_path, "r") as f:
                gdrive_links = json.load(f)
        except:
            pass
            
    gdrive_video_link = ""
    if gdrive_links:
        gdrive_video_link = gdrive_links.get("video", "")
    else:
        # Fallback to single link if json is missing
        if os.path.exists(gdrive_link_path):
            try:
                with open(gdrive_link_path, "r") as f:
                    gdrive_video_link = f.read().strip()
            except:
                pass
            
    youtube_link = ""
    if os.path.exists(youtube_link_path):
        try:
            with open(youtube_link_path, "r") as f:
                youtube_link = f.read().strip()
        except:
            pass
            
    # If failure occurred, log to sheet as failed if sheets setup exists
    if error_occurred:
        try:
            log_to_sheets(youtube_link=youtube_link, gdrive_links=gdrive_links, status="failed")
        except:
            pass
 
    # Send final report to Telegram
    notify_pipeline_status(
        pipeline_state=state,
        video_title=video_title,
        article_url=article_url,
        youtube_link=youtube_link,
        gdrive_link=gdrive_video_link,
        error_message=error_msg if error_occurred else ""
    )
    
    if error_occurred:
        logger.error(f"Pipeline execution halted with errors: {error_msg}")
        sys.exit(1)
        
    logger.info("==================================================")
    logger.info(" PIPELINE COMPLETED SUCCESSFULLY! RUN SUMMARY SENT.")
    logger.info("==================================================")

if __name__ == "__main__":
    main()
