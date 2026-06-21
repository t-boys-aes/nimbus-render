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

def fetch_pexels_footage(keyword: str, dest_path: str) -> bool:
    """Fetch video from Pexels API matching keyword."""
    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY not configured. Skipping Pexels search.")
        return False

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
            return False
            
        # Extract the best video file
        best_url = None
        for video in videos:
            files = video.get("video_files", [])
            # Prefer HD or SD mp4 video with width 1920 or 1280
            for file in files:
                file_type = file.get("file_type", "")
                if "mp4" in file_type or not file_type:
                    w = file.get("width")
                    if w == 1920 or w == 1280:
                        best_url = file.get("link")
                        break
            if best_url:
                break
                
        # Fallback to the first video file link if no perfect match
        if not best_url and videos:
            video_files = videos[0].get("video_files", [])
            if video_files:
                best_url = video_files[0].get("link")
                
        if best_url:
            return download_video_file(best_url, dest_path)
            
        return False
    except Exception as e:
        logger.error(f"Pexels search error: {e}")
        return False

def fetch_pixabay_footage(keyword: str, dest_path: str) -> bool:
    """Fetch video from Pixabay API matching keyword."""
    if not PIXABAY_API_KEY:
        logger.warning("PIXABAY_API_KEY not configured. Skipping Pixabay search.")
        return False

    logger.info(f"Searching Pixabay for keyword: '{keyword}'")
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={keyword}&orientation=horizontal"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        hits = data.get("hits", [])
        if not hits:
            logger.warning(f"No videos found on Pixabay for: '{keyword}'")
            return False
            
        # Extract video URL (Pixabay provides multiple size URLs under 'videos')
        videos_map = hits[0].get("videos", {})
        # Try medium, large, small
        best_video = videos_map.get("medium") or videos_map.get("large") or videos_map.get("small")
        if best_video:
            video_url = best_video.get("url")
            return download_video_file(video_url, dest_path)
            
        return False
    except Exception as e:
        logger.error(f"Pixabay search error: {e}")
        return False

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
    
    for i, seg in enumerate(segments):
        visual_type = seg.get("visual_type", "footage")
        keyword = seg.get("visual_keyword", "business")
        dest_path = os.path.join(FOOTAGE_DIR, f"segment_{i}.mp4")
        
        success = False
        if visual_type == "footage":
            # Try Pexels first
            success = fetch_pexels_footage(keyword, dest_path)
            # Try Pixabay if Pexels fails
            if not success:
                success = fetch_pixabay_footage(keyword, dest_path)
                
        # If successfully downloaded a clip or it's a chart/map, skip placeholder
        # Note: chart/map visual types are generated dynamically in the renderer,
        # so we also mark them as placeholders to be built by our Python script.
        if not success or visual_type in ["chart", "map"]:
            create_local_placeholder(i, visual_type, keyword, dest_path)
            
    logger.info("Footage fetching phase completed.")

if __name__ == "__main__":
    logger.info("Running footage fetcher standalone test...")
    try:
        fetch_all_footage()
    except Exception as e:
        logger.error(f"Footage fetcher test failed: {e}")
