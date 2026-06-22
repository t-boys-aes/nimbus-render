import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
BGM_MOODS = {
    "suspenseful": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "ambient": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
    "motivational": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
    "corporate": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3"
}
SFX_URLS = {
    "whoosh": "https://remotion.media/whoosh.wav",
    "pop": "https://remotion.media/mouse-click.wav"
}
FONT_URL = "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf"
GEOJSON_URL = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"

ASSETS_DIR = os.path.join("temp", "assets")
BGM_PATH = os.path.join(ASSETS_DIR, "bgm.mp3")
SFX_PATH = os.path.join(ASSETS_DIR, "transition_sfx.wav")
SFX_POP_PATH = os.path.join(ASSETS_DIR, "subtle_pop.wav")
FONT_PATH = os.path.join(ASSETS_DIR, "font.ttf")
GEOJSON_PATH = os.path.join(ASSETS_DIR, "world.geo.json")
SCRIPT_DATA_PATH = os.path.join("temp", "script_data.json")

def download_file(url: str, dest_path: str, retries: int = 5):
    """Download a file from a URL to a destination path with retry logic."""
    if os.path.exists(dest_path):
        logger.info(f"File already exists: {dest_path}")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for attempt in range(1, retries + 1):
        logger.info(f"Downloading from {url} to {dest_path} (Attempt {attempt}/{retries})...")
        tmp_path = dest_path + ".tmp"
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            with open(tmp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=16384):  # Use larger chunk size (16KB)
                    if chunk:
                        f.write(chunk)
            
            # Rename temp file to final destination upon success
            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(tmp_path, dest_path)
            logger.info(f"Successfully downloaded: {dest_path}")
            return
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            if attempt == retries:
                logger.error(f"All {retries} download attempts failed.")
                raise e

def verify_ffmpeg():
    """Verify that FFmpeg is available through imageio-ffmpeg."""
    logger.info("Verifying FFmpeg path via imageio_ffmpeg...")
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        logger.info(f"FFmpeg is successfully configured at: {ffmpeg_exe}")
        return ffmpeg_exe
    except ImportError:
        logger.error("imageio-ffmpeg is not installed.")
        raise ImportError("imageio-ffmpeg package is missing. Please check requirements installation.")
    except Exception as e:
        logger.error(f"FFmpeg verification failed: {e}")
        raise e

def setup_assets():
    """Ensure all required assets are downloaded and verified."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    # 1. Determine background music URL based on generated AI mood
    bgm_url = BGM_MOODS["suspenseful"] # Default fallback
    if os.path.exists(SCRIPT_DATA_PATH):
        try:
            import json
            with open(SCRIPT_DATA_PATH, "r", encoding="utf-8") as f:
                script_data = json.load(f)
            mood = script_data.get("music_mood", "suspenseful").lower()
            if mood in BGM_MOODS:
                bgm_url = BGM_MOODS[mood]
                logger.info(f"Selected BGM URL for mood '{mood}': {bgm_url}")
        except Exception as e:
            logger.warning(f"Failed to read script mood, using default BGM. Error: {e}")
            
    # Download background music
    download_file(bgm_url, BGM_PATH)
    
    # 2. Download sound effects (Whoosh & Pop)
    download_file(SFX_URLS["whoosh"], SFX_PATH)
    download_file(SFX_URLS["pop"], SFX_POP_PATH)
    
    # 3. Download custom premium font
    download_file(FONT_URL, FONT_PATH)
    
    # 4. Download world GeoJSON map
    download_file(GEOJSON_URL, GEOJSON_PATH)
    
    # 5. Verify FFmpeg
    ffmpeg_path = verify_ffmpeg()
    
    return {
        "bgm": BGM_PATH,
        "sfx": SFX_PATH,
        "sfx_pop": SFX_POP_PATH,
        "font": FONT_PATH,
        "geojson": GEOJSON_PATH,
        "ffmpeg": ffmpeg_path
    }

if __name__ == "__main__":
    logger.info("Starting asset downloader...")
    try:
        paths = setup_assets()
        logger.info("All assets successfully setup!")
        logger.info(f"BGM Path: {paths['bgm']}")
        logger.info(f"SFX Path: {paths['sfx']}")
    except Exception as e:
        logger.error(f"Asset setup failed: {e}")
