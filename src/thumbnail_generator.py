import os
import json
import logging
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEMP_DIR = "temp"
OUTPUT_DIR = "output"
ASSETS_DIR = os.path.join(TEMP_DIR, "assets")
FONT_PATH = os.path.join(ASSETS_DIR, "font.ttf")
SCRIPT_DATA_PATH = os.path.join(TEMP_DIR, "script_data.json")

THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720

def extract_first_frame(video_path: str) -> Image.Image:
    """Extract the first frame of a video clip as a Pillow image."""
    logger.info(f"Extracting first frame from video: {video_path}")
    try:
        clip = VideoFileClip(video_path)
        # Extract frame at t=0
        frame = clip.get_frame(0)
        img = Image.fromarray(frame)
        clip.close()
        return img
    except Exception as e:
        logger.warning(f"Failed to extract frame from video: {e}. Falling back to gradient.")
        return None

def create_gradient_background() -> Image.Image:
    """Generate a premium dark gradient background."""
    logger.info("Generating gradient background for thumbnail...")
    img = Image.new("RGB", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), color="#080b11")
    draw = ImageDraw.Draw(img)
    
    # Draw horizontal linear gradient
    for x in range(THUMBNAIL_WIDTH):
        r = int(8 + (24 - 8) * (x / THUMBNAIL_WIDTH))
        g = int(11 + (29 - 11) * (x / THUMBNAIL_WIDTH))
        b = int(17 + (38 - 17) * (x / THUMBNAIL_WIDTH))
        draw.line([(x, 0), (x, THUMBNAIL_HEIGHT)], fill=(r, g, b))
        
    # Draw tech grid overlay
    for x in range(0, THUMBNAIL_WIDTH, 80):
        draw.line([(x, 0), (x, THUMBNAIL_HEIGHT)], fill="#1a202c", width=1)
    for y in range(0, THUMBNAIL_HEIGHT, 80):
        draw.line([(0, y), (THUMBNAIL_WIDTH, y)], fill="#1a202c", width=1)
        
    return img

def apply_cinematic_overlay(img: Image.Image) -> Image.Image:
    """Apply dark horizontal gradient vignette overlay (dark on the left)."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Left shadow gradient (for text readability)
    for x in range(THUMBNAIL_WIDTH):
        alpha = int(230 * (1.0 - min(1.0, x / (THUMBNAIL_WIDTH * 0.7))))
        if alpha > 0:
            draw.line([(x, 0), (x, THUMBNAIL_HEIGHT)], fill=(0, 0, 0, alpha))
            
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

def draw_thumbnail_text(img: Image.Image, text: str):
    """Draw bold, premium, drop-shadowed text on the thumbnail."""
    draw = ImageDraw.Draw(img)
    
    try:
        if os.path.exists(FONT_PATH):
            font = ImageFont.truetype(FONT_PATH, 75)
        else:
            font = ImageFont.truetype("arial.ttf", 75)
    except IOError:
        font = ImageFont.load_default()
        
    # Split text into lines (max 3 words per line for large text)
    words = text.upper().split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(current_line) >= 3:
            lines.append(" ".join(current_line))
            current_line = []
    if current_line:
        lines.append(" ".join(current_line))
        
    # Draw multiline text on the left-middle side of the cover
    start_y = 200
    line_spacing = 90
    
    for idx, line in enumerate(lines):
        y = start_y + (idx * line_spacing)
        x = 80  # Left margin
        
        is_last_line = (idx == len(lines) - 1)
        line_words = line.split()
        
        if is_last_line and len(line_words) > 1:
            base_text = " ".join(line_words[:-1]) + " "
            last_word = line_words[-1]
            
            if hasattr(draw, "textbbox"):
                bbox = draw.textbbox((0, 0), base_text, font=font)
                w_base = bbox[2] - bbox[0]
            elif hasattr(draw, "textsize"):
                w_base, _ = draw.textsize(base_text, font=font)
            else:
                w_base = len(base_text) * 35
                
            # Draw shadow
            draw.text((x + 4, y + 4), base_text, fill=(0, 0, 0, 180), font=font)
            draw.text((x + w_base + 4, y + 4), last_word, fill=(0, 0, 0, 180), font=font)
            
            # Draw actual text
            draw.text((x, y), base_text, fill="#ffffff", font=font)
            draw.text((x + w_base, y), last_word, fill="#ffeb3b", font=font)
        else:
            # Draw full line in white
            draw.text((x + 4, y + 4), line, fill=(0, 0, 0, 180), font=font)
            draw.text((x, y), line, fill="#ffffff", font=font)

def generate_thumbnail():
    """Main entry point to build and save the YouTube cover thumbnail."""
    logger.info("Starting YouTube cover thumbnail generator...")
    
    if not os.path.exists(SCRIPT_DATA_PATH):
        raise FileNotFoundError(f"Script data not found at {SCRIPT_DATA_PATH}")
        
    with open(SCRIPT_DATA_PATH, "r", encoding="utf-8") as f:
        script_data = json.load(f)
        
    text = script_data.get("thumbnail_text", "GLOBAL GEOPOLITICS")
    logger.info(f"Thumbnail text: '{text}'")
    
    video_path = os.path.join(TEMP_DIR, "footage", "segment_0.mp4")
    background_img = None
    if os.path.exists(video_path):
        background_img = extract_first_frame(video_path)
        
    if background_img:
        background_img = background_img.resize((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT))
    else:
        background_img = create_gradient_background()
        
    cover = apply_cinematic_overlay(background_img)
    draw_thumbnail_text(cover, text)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "thumbnail.png")
    cover.save(out_path, "PNG")
    logger.info(f"Successfully generated YouTube thumbnail at: {out_path}")
    return out_path

if __name__ == "__main__":
    try:
        generate_thumbnail()
    except Exception as e:
        logger.error(f"Thumbnail generator failed: {e}")
