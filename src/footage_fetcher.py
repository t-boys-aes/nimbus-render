import os
import json
import requests
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TEMP_DIR = "temp"
SCRIPT_DATA_PATH = os.path.join(TEMP_DIR, "script_data.json")
FOOTAGE_DIR = os.path.join(TEMP_DIR, "footage")
USED_LOG_PATH = "used_footage_log.json"

# API Keys
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")

COOLDOWN_RUNS = 5

def load_used_footage_log() -> dict:
    """Load the used footage log mapping video ID strings to the run index they were used in."""
    if os.path.exists(USED_LOG_PATH):
        try:
            with open(USED_LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read used footage log: {e}")
    return {"current_run_index": 0, "history": {}}

def save_used_footage_log(log_data: dict):
    """Save the used footage log to file."""
    try:
        with open(USED_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to write used footage log: {e}")

def download_video_file(url: str, dest_path: str) -> bool:
    """Download video content from URL to local file."""
    logger.info(f"Downloading video from {url} to {dest_path}...")
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
        logger.info(f"Finished downloading footage: {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download video file: {e}")
        return False

def fetch_pexels_footage(keyword: str, dest_path: str, run_log: dict) -> tuple:
    """Fetch video from Pexels API matching keyword. Returns (success, author, url)."""
    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY not configured. Skipping Pexels search.")
        return False, "", ""

    logger.info(f"Searching Pexels for keyword: '{keyword}'")
    headers = {"Authorization": PEXELS_API_KEY}
    # Increase per_page to 15 to have alternatives when some videos are in cooldown
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=15&orientation=landscape"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        videos = data.get("videos", [])
        if not videos:
            logger.warning(f"No videos found on Pexels for: '{keyword}'")
            return False, "", ""
            
        current_run = run_log.get("current_run_index", 1)
        history = run_log.get("history", {})
        
        available_videos = []
        cooldown_videos = [] # Fallback list
        
        for video in videos:
            video_id = str(video.get("id"))
            last_used = history.get(video_id, -999)
            
            # Extract best video file
            best_url = None
            files = video.get("video_files", [])
            for file in files:
                file_type = file.get("file_type", "")
                if "mp4" in file_type or not file_type:
                    w = file.get("width")
                    if w == 1920 or w == 1280:
                        best_url = file.get("link")
                        break
            
            # Fallback if no perfect match
            if not best_url and files:
                best_url = files[0].get("link")
                
            if best_url:
                video_item = {
                    "id": video_id,
                    "url": best_url,
                    "author_name": video.get("user", {}).get("name", "Unknown"),
                    "author_url": video.get("user", {}).get("url", ""),
                    "last_used": last_used
                }
                
                # Check cooldown condition
                if current_run - last_used >= COOLDOWN_RUNS:
                    available_videos.append(video_item)
                else:
                    cooldown_videos.append(video_item)
                    
        # Pick the best choice (randomly choose from top 3 fresh candidates for variety)
        chosen_video = None
        if available_videos:
            import random
            candidates = available_videos[:3]
            chosen_video = random.choice(candidates)
            logger.info(f"Selected fresh Pexels video ID: {chosen_video['id']} (randomly chosen from {len(candidates)} candidates)")
        elif cooldown_videos:
            cooldown_videos.sort(key=lambda x: x["last_used"])
            chosen_video = cooldown_videos[0]
            logger.warning(f"All Pexels videos in cooldown. Selected oldest used ID: {chosen_video['id']} (last used in run {chosen_video['last_used']})")
            
        if chosen_video:
            success = download_video_file(chosen_video["url"], dest_path)
            if success:
                history[chosen_video["id"]] = current_run
                return True, chosen_video["author_name"], chosen_video["author_url"]
                
        return False, "", ""
    except Exception as e:
        logger.error(f"Pexels search error: {e}")
        return False, "", ""

def fetch_pixabay_footage(keyword: str, dest_path: str, run_log: dict) -> tuple:
    """Fetch video from Pixabay API matching keyword. Returns (success, author, url)."""
    if not PIXABAY_API_KEY:
        logger.warning("PIXABAY_API_KEY not configured. Skipping Pixabay search.")
        return False, "", ""

    logger.info(f"Searching Pixabay for keyword: '{keyword}'")
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={keyword}&orientation=horizontal&per_page=15"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        hits = data.get("hits", [])
        if not hits:
            logger.warning(f"No videos found on Pixabay for: '{keyword}'")
            return False, "", ""
            
        current_run = run_log.get("current_run_index", 1)
        history = run_log.get("history", {})
        
        available_videos = []
        cooldown_videos = []
        
        for hit in hits:
            video_id = str(hit.get("id"))
            last_used = history.get(video_id, -999)
            
            videos_map = hit.get("videos", {})
            best_video = videos_map.get("medium") or videos_map.get("large") or videos_map.get("small")
            
            if best_video:
                video_url = best_video.get("url")
                video_item = {
                    "id": video_id,
                    "url": video_url,
                    "author_name": hit.get("user", "Unknown"),
                    "author_url": f"https://pixabay.com/users/{hit.get('user')}/" if hit.get("user") != "Unknown" else "",
                    "last_used": last_used
                }
                
                if current_run - last_used >= COOLDOWN_RUNS:
                    available_videos.append(video_item)
                else:
                    cooldown_videos.append(video_item)
                    
        # Pick the best choice (randomly choose from top 3 fresh candidates for variety)
        chosen_video = None
        if available_videos:
            import random
            candidates = available_videos[:3]
            chosen_video = random.choice(candidates)
            logger.info(f"Selected fresh Pixabay video ID: {chosen_video['id']} (randomly chosen from {len(candidates)} candidates)")
        elif cooldown_videos:
            cooldown_videos.sort(key=lambda x: x["last_used"])
            chosen_video = cooldown_videos[0]
            logger.warning(f"All Pixabay videos in cooldown. Selected oldest used ID: {chosen_video['id']} (last used in run {chosen_video['last_used']})")
            
        if chosen_video:
            success = download_video_file(chosen_video["url"], dest_path)
            if success:
                history[chosen_video["id"]] = current_run
                return True, chosen_video["author_name"], chosen_video["author_url"]
                
        return False, "", ""
    except Exception as e:
        logger.error(f"Pixabay search error: {e}")
        return False, "", ""

def create_local_placeholder(index: int, visual_type: str, keyword: str, dest_path: str):
    """Save metadata info to create a placeholder clip later in the renderer."""
    logger.info(f"Creating local placeholder config for segment {index} ({visual_type}: {keyword})")
    placeholder_info = {
        "visual_type": visual_type,
        "keyword": keyword,
        "is_placeholder": True
    }
    placeholder_path = dest_path + ".placeholder.json"
    with open(placeholder_path, "w", encoding="utf-8") as f:
        json.dump(placeholder_info, f, indent=4)

def fetch_all_footage():
    """Download video assets for all segments in script."""
    if not os.path.exists(SCRIPT_DATA_PATH):
        raise FileNotFoundError(f"Script data file not found at {SCRIPT_DATA_PATH}. Please run script_generator first.")
        
    os.makedirs(FOOTAGE_DIR, exist_ok=True)
    
    # Load and increment the production run index
    run_log = load_used_footage_log()
    run_log["current_run_index"] = run_log.get("current_run_index", 0) + 1
    logger.info(f"==================================================")
    logger.info(f" PRODUCTION RUN INDEX: {run_log['current_run_index']}")
    logger.info(f"==================================================")
    
    with open(SCRIPT_DATA_PATH, "r", encoding="utf-8") as f:
        script_data = json.load(f)
        
    segments = script_data.get("segments", [])
    logger.info(f"Starting footage fetcher for {len(segments)} segments...")
    
    attributions = {}
    
    for i, seg in enumerate(segments):
        visual_type = seg.get("visual_type", "footage")
        keyword = seg.get("visual_keyword", "business")
        dest_path = os.path.join(FOOTAGE_DIR, f"segment_{i}.mp4")
        
        success = False
        author = ""
        url = ""
        
        if visual_type == "footage":
            import random
            # Randomly decide which API to prioritize (50/50 chance)
            use_pexels_first = random.choice([True, False])
            
            if use_pexels_first:
                logger.info(f"Trying Pexels API first for segment {i}")
                success, author, url = fetch_pexels_footage(keyword, dest_path, run_log)
                if success:
                    attributions[f"segment_{i}"] = {
                        "author": author,
                        "url": url,
                        "keyword": keyword,
                        "source": "Pexels"
                    }
                else:
                    logger.info(f"Pexels failed, falling back to Pixabay for segment {i}")
                    success, author, url = fetch_pixabay_footage(keyword, dest_path, run_log)
                    if success:
                        attributions[f"segment_{i}"] = {
                            "author": author,
                            "url": url,
                            "keyword": keyword,
                            "source": "Pixabay"
                        }
            else:
                logger.info(f"Trying Pixabay API first for segment {i}")
                success, author, url = fetch_pixabay_footage(keyword, dest_path, run_log)
                if success:
                    attributions[f"segment_{i}"] = {
                        "author": author,
                        "url": url,
                        "keyword": keyword,
                        "source": "Pixabay"
                    }
                else:
                    logger.info(f"Pixabay failed, falling back to Pexels for segment {i}")
                    success, author, url = fetch_pexels_footage(keyword, dest_path, run_log)
                    if success:
                        attributions[f"segment_{i}"] = {
                            "author": author,
                            "url": url,
                            "keyword": keyword,
                            "source": "Pexels"
                        }
                
        # If successfully downloaded a clip or it's a chart/map/timeline, skip placeholder
        if not success or visual_type in ["chart", "map", "clipping", "quote", "stat", "timeline"]:
            create_local_placeholder(i, visual_type, keyword, dest_path)
        else:
            # Clean up any leftover placeholder config from previous runs
            placeholder_path = dest_path + ".placeholder.json"
            if os.path.exists(placeholder_path):
                try:
                    os.remove(placeholder_path)
                    logger.info(f"Cleaned up old placeholder config: {placeholder_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete old placeholder config: {e}")
            
    # Save the updated run log
    save_used_footage_log(run_log)
    
    # Save attributions JSON
    attributions_path = os.path.join(TEMP_DIR, "footage_attributions.json")
    with open(attributions_path, "w", encoding="utf-8") as f:
        json.dump(attributions, f, indent=4)
    logger.info(f"Saved footage attributions to {attributions_path}")
    logger.info("Footage fetching phase completed.")

if __name__ == "__main__":
    logger.info("Running footage fetcher standalone test...")
    try:
        fetch_all_footage()
    except Exception as e:
        logger.error(f"Footage fetcher test failed: {e}")
