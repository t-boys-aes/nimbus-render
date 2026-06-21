import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
BGM_URL = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
SFX_URL = "https://remotion.media/whoosh.wav"
FONT_URL = "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf"

ASSETS_DIR = os.path.join("temp", "assets")
BGM_PATH = os.path.join(ASSETS_DIR, "bgm.mp3")
SFX_PATH = os.path.join(ASSETS_DIR, "transition_sfx.wav")
FONT_PATH = os.path.join(ASSETS_DIR, "font.ttf")

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
    
    # Download background music
    download_file(BGM_URL, BGM_PATH)
    
    # Download sound effects
    download_file(SFX_URL, SFX_PATH)
    
    # Download custom premium font
    download_file(FONT_URL, FONT_PATH)
    
    # Verify FFmpeg
    ffmpeg_path = verify_ffmpeg()
    
    return {
        "bgm": BGM_PATH,
        "sfx": SFX_PATH,
        "font": FONT_PATH,
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
