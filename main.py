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

# Define ordered pipeline steps
PIPELINE_STEPS = ["assets", "news", "script", "tts", "footage", "render", "thumbnail"]

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
    
    args = parser.parse_args()
    
    state = load_state()
    
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
        
    # 3. Main pipeline loop
    for step in PIPELINE_STEPS:
        # If resuming and step was already successful, skip it
        if args.resume and state.get(step) == "success":
            logger.info(f"Skipping already completed step: {step.upper()}")
            continue
            
        success = run_step(step, url_override=args.url)
        state[step] = "success" if success else "failed"
        save_state(state)
        
        if not success:
            logger.error(f"Pipeline execution halted at step '{step.upper()}'. Repair the issue and run with --resume.")
            sys.exit(1)
            
    logger.info("==================================================")
    logger.info(" PIPELINE COMPLETED SUCCESSFULLY! VIDEO READY.")
    logger.info("==================================================")

if __name__ == "__main__":
    main()
