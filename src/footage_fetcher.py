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

# API Keys
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")

def download_video_file(url: str, dest_path: str):
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

def fetch_pexels_footage(keyword: str, dest_path: str) -> tuple:
    """Fetch video from Pexels API matching keyword. Returns (success, author, url)."""
    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY not configured. Skipping Pexels search.")
        return False, "", ""

    logger.info(f"Searching Pexels for keyword: '{keyword}'")
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=3&orientation=landscape"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        videos = data.get("videos", [])
        if not videos:
            logger.warning(f"No videos found on Pexels for: '{keyword}'")
            return False, "", ""
            
        # Extract the best video file and author info
        best_url = None
        author_name = "Unknown"
        author_url = ""
        for video in videos:
            files = video.get("video_files", [])
            # Prefer HD or SD mp4 video with width 1920 or 1280
            for file in files:
                file_type = file.get("file_type", "")
                if "mp4" in file_type or not file_type:
                    w = file.get("width")
                    if w == 1920 or w == 1280:
                        best_url = file.get("link")
                        author_name = video.get("user", {}).get("name", "Unknown")
                        author_url = video.get("user", {}).get("url", "")
                        break
            if best_url:
                break
                
        # Fallback to the first video file link if no perfect match
        if not best_url and videos:
            video_files = videos[0].get("video_files", [])
            if video_files:
                best_url = video_files[0].get("link")
                author_name = videos[0].get("user", {}).get("name", "Unknown")
                author_url = videos[0].get("user", {}).get("url", "")
                
        if best_url:
            success = download_video_file(best_url, dest_path)
            return success, author_name, author_url
            
        return False, "", ""
    except Exception as e:
        logger.error(f"Pexels search error: {e}")
        return False, "", ""

def fetch_pixabay_footage(keyword: str, dest_path: str) -> tuple:
    """Fetch video from Pixabay API matching keyword. Returns (success, author, url)."""
    if not PIXABAY_API_KEY:
        logger.warning("PIXABAY_API_KEY not configured. Skipping Pixabay search.")
        return False, "", ""

    logger.info(f"Searching Pixabay for keyword: '{keyword}'")
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={keyword}&orientation=horizontal"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        hits = data.get("hits", [])
        if not hits:
            logger.warning(f"No videos found on Pixabay for: '{keyword}'")
            return False, "", ""
            
        # Extract video URL and author details
        videos_map = hits[0].get("videos", {})
        best_video = videos_map.get("medium") or videos_map.get("large") or videos_map.get("small")
        author_name = hits[0].get("user", "Unknown")
        author_url = f"https://pixabay.com/users/{author_name}/" if author_name != "Unknown" else ""
        
        if best_video:
            video_url = best_video.get("url")
            success = download_video_file(video_url, dest_path)
            return success, author_name, author_url
            
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
            # Try Pexels first
            success, author, url = fetch_pexels_footage(keyword, dest_path)
            if success:
                attributions[f"segment_{i}"] = {
                    "author": author,
                    "url": url,
                    "keyword": keyword,
                    "source": "Pexels"
                }
            else:
                # Try Pixabay if Pexels fails
                success, author, url = fetch_pixabay_footage(keyword, dest_path)
                if success:
                    attributions[f"segment_{i}"] = {
                        "author": author,
                        "url": url,
                        "keyword": keyword,
                        "source": "Pixabay"
                    }
                
        # If successfully downloaded a clip or it's a chart/map, skip placeholder
        # Note: chart/map visual types are generated dynamically in the renderer,
        # so we also mark them as placeholders to be built by our Python script.
        if not success or visual_type in ["chart", "map"]:
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
