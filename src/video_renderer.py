import os
import json
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Use non-GUI backend for matplotlib
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, CompositeAudioClip, concatenate_videoclips
import moviepy.video.fx as vfx
import moviepy.audio.fx as afx

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
TEMP_DIR = "temp"
OUTPUT_DIR = "output"
SCRIPT_DATA_PATH = os.path.join(TEMP_DIR, "script_data.json")
TTS_DIR = os.path.join(TEMP_DIR, "tts")
FOOTAGE_DIR = os.path.join(TEMP_DIR, "footage")
ASSETS_DIR = os.path.join(TEMP_DIR, "assets")

BGM_PATH = os.path.join(ASSETS_DIR, "bgm.mp3")
SFX_PATH = os.path.join(ASSETS_DIR, "transition_sfx.wav")

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 24

def generate_matplotlib_chart(keyword: str, out_path: str):
    """Generate a clean dark-mode chart based on keyword and save as PNG."""
    logger.info(f"Generating chart for keyword '{keyword}' -> {out_path}")
    
    # Set dark theme for matplotlib
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    fig.patch.set_facecolor("#121214")
    ax.set_facecolor("#1e1e24")
    
    # Simple data variation based on keyword
    if "inflation" in keyword.lower():
        years = [2021, 2022, 2023, 2024, 2025, 2026]
        rates = [2.5, 4.7, 6.5, 4.1, 3.2, 2.8]
        ax.plot(years, rates, marker='o', linewidth=3, color='#ff5a5f', markersize=8, label="Inflation Rate (%)")
        ax.set_title("Global Inflation Trend (2021 - 2026)", fontsize=16, color='#ffffff', pad=15)
        ax.set_ylabel("Percentage (%)", fontsize=12)
        ax.grid(True, color="#444444", linestyle="--")
    elif "gdp" in keyword.lower() or "growth" in keyword.lower():
        labels = ["US", "China", "Eurozone", "India", "Japan"]
        growth = [2.1, 4.8, 0.8, 6.8, 1.0]
        colors = ["#3a86c8", "#e63946", "#f4a261", "#2a9d8f", "#e9c46a"]
        ax.bar(labels, growth, color=colors, width=0.6)
        ax.set_title("GDP Growth Comparison (%)", fontsize=16, color='#ffffff', pad=15)
        ax.set_ylabel("Growth Rate (%)", fontsize=12)
    else:
        # Default chart
        labels = ["A", "B", "C", "D", "E"]
        values = [10, 24, 15, 30, 20]
        ax.plot(labels, values, marker='s', linewidth=2, color='#00b4d8', markersize=6)
        ax.set_title(f"Market Index: {keyword.upper()}", fontsize=16, color='#ffffff', pad=15)
        ax.grid(True, color="#444444", linestyle="--")

    # Clean axes
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#888888')
    ax.spines['bottom'].set_color('#888888')
    ax.tick_params(colors='#cccccc', labelsize=10)
    
    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

def generate_map_infographic(keyword: str, out_path: str):
    """Generate a clean geopolitical map infographic card and save as PNG."""
    logger.info(f"Generating map card for keyword '{keyword}' -> {out_path}")
    
    # Create dark gradient background
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color="#0c0d12")
    draw = ImageDraw.Draw(img)
    
    # Draw simple grid pattern for tech look
    for x in range(0, VIDEO_WIDTH, 80):
        draw.line([(x, 0), (x, VIDEO_HEIGHT)], fill="#1a1c24", width=1)
    for y in range(0, VIDEO_HEIGHT, 80):
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill="#1a1c24", width=1)
        
    # Draw an outer glowing border
    draw.rectangle([(20, 20), (VIDEO_WIDTH-20, VIDEO_HEIGHT-20)], outline="#00b4d8", width=3)
    
    # Draw title / header
    font_path = os.path.join(ASSETS_DIR, "font.ttf")
    try:
        if os.path.exists(font_path):
            header_font = ImageFont.truetype(font_path, 36)
            title_font = ImageFont.truetype(font_path, 64)
            info_font = ImageFont.truetype(font_path, 28)
        else:
            header_font = ImageFont.truetype("arial.ttf", 36)
            title_font = ImageFont.truetype("arial.ttf", 64)
            info_font = ImageFont.truetype("arial.ttf", 28)
    except IOError:
        header_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
        
    draw.text((80, 80), "NIMBUS GLOBAL INTELLIGENCE", fill="#888888", font=header_font)
    draw.text((80, 140), f"GEOPOLITICAL ZONE: {keyword.upper()}", fill="#ffffff", font=title_font)
    
    # Draw a mock world map graphic (concentric radar circles + dots)
    center_x, center_y = 960, 560
    draw.ellipse([(center_x-200, center_y-200), (center_x+200, center_y+200)], outline="#1d3557", width=2)
    draw.ellipse([(center_x-100, center_y-100), (center_x+100, center_y+100)], outline="#1d3557", width=2)
    draw.line([(center_x-300, center_y), (center_x+300, center_y)], fill="#1d3557", width=2)
    draw.line([(center_x, center_y-300), (center_x, center_y+300)], fill="#1d3557", width=2)
    
    # Mock data dots (coordinates highlight)
    draw.ellipse([(center_x-50, center_y-30), (center_x-40, center_y-20)], fill="#e63946") # Point A
    draw.ellipse([(center_x+120, center_y+80), (center_x+130, center_y+90)], fill="#457b9d") # Point B
    
    # Info label
    draw.text((80, VIDEO_HEIGHT-200), "STATUS: ACTIVE MONITORING\nDATA TYPE: SATELLITE OVERLAY / REGIONAL MAP", fill="#00b4d8", font=info_font)
    
    img.save(out_path)

def generate_gradient_background(keyword: str, out_path: str):
    """Generate a clean dark gradient image for missing footage and save as PNG."""
    logger.info(f"Generating gradient background -> {out_path}")
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color="#08090d")
    draw = ImageDraw.Draw(img)
    
    # Draw tech grid
    for x in range(0, VIDEO_WIDTH, 100):
        draw.line([(x, 0), (x, VIDEO_HEIGHT)], fill="#141722", width=1)
    for y in range(0, VIDEO_HEIGHT, 100):
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill="#141722", width=1)
        
    font_path = os.path.join(ASSETS_DIR, "font.ttf")
    try:
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, 60)
            sub_font = ImageFont.truetype(font_path, 32)
        else:
            font = ImageFont.truetype("arial.ttf", 60)
            sub_font = ImageFont.truetype("arial.ttf", 32)
    except IOError:
        font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
        
    # Draw keyword header
    draw.text((100, 100), f"[ {keyword.upper()} ]", fill="#00b4d8", font=font)
    draw.text((100, 180), "SYSTEM FEED / CONCEPTUAL PREVIEW", fill="#555555", font=sub_font)
    
    img.save(out_path)

def make_subtitle_filter(timestamps):
    """Return a filter function that draws text overlay with outline on each frame."""
    def filter_func(get_frame, t):
        frame = get_frame(t)
        
        # Find active word
        active_word = ""
        for word_data in timestamps:
            if word_data["start"] <= t <= word_data["end"]:
                active_word = word_data["word"].upper()
                break
                
        if not active_word:
            return frame
            
        # Convert frame to Pillow
        img = Image.fromarray(frame)
        draw = ImageDraw.Draw(img)
        
        # Load font
        font_path = os.path.join(ASSETS_DIR, "font.ttf")
        try:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 80)
            else:
                font = ImageFont.truetype("arial.ttf", 80)
        except IOError:
            font = ImageFont.load_default()
            
        # Draw word centered near the bottom (karaoke pop effect)
        # Using a solid bounding box + text outline for maximum visibility
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), active_word, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        elif hasattr(draw, "textsize"):
            w, h = draw.textsize(active_word, font=font)
        else:
            w, h = len(active_word) * 35, 70
            
        x = (VIDEO_WIDTH - w) // 2
        y = VIDEO_HEIGHT - 220
        
        # Draw background card for text readability
        draw.rectangle([(x-20, y-10), (x+w+20, y+h+10)], fill=(0, 0, 0, 180))
        
        # Draw text with outline
        draw.text((x, y), active_word, fill="#ffeb3b", font=font)  # Bright yellow highlighted word
        
        return np.array(img)
    return filter_func

def build_video_segments():
    """Main rendering loop: builds each segment's video clip, and concatenates them."""
    if not os.path.exists(SCRIPT_DATA_PATH):
        raise FileNotFoundError(f"Script data not found: {SCRIPT_DATA_PATH}")
        
    with open(SCRIPT_DATA_PATH, "r", encoding="utf-8") as f:
        script_data = json.load(f)
        
    segments = script_data.get("segments", [])
    logger.info(f"Rendering {len(segments)} segments...")
    
    video_clips = []
    
    for i, seg in enumerate(segments):
        visual_type = seg.get("visual_type", "footage")
        keyword = seg.get("visual_keyword", "business")
        
        audio_path = os.path.join(TTS_DIR, f"segment_{i}.mp3")
        timestamp_path = os.path.join(TTS_DIR, f"timestamps_{i}.json")
        footage_path = os.path.join(FOOTAGE_DIR, f"segment_{i}.mp4")
        placeholder_conf = footage_path + ".placeholder.json"
        
        if not os.path.exists(audio_path):
            logger.error(f"Missing audio for segment {i}, skipping.")
            continue
            
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 1. Base Visual Clip
        base_clip = None
        
        # Check if actual video footage exists
        if os.path.exists(footage_path) and not os.path.exists(placeholder_conf):
            logger.info(f"Segment {i}: Loading video footage {footage_path}")
            base_clip = VideoFileClip(footage_path).without_audio()
            # Loop video if it is shorter than audio, trim if longer
            if base_clip.duration < duration:
                base_clip = base_clip.with_effects([vfx.Loop(duration=duration)])
            else:
                base_clip = base_clip.with_duration(duration)
        else:
            # Generate visual image based on visual_type
            image_path = os.path.join(TEMP_DIR, f"visual_{i}.png")
            if visual_type == "chart":
                generate_matplotlib_chart(keyword, image_path)
            elif visual_type == "map":
                generate_map_infographic(keyword, image_path)
            else:
                generate_gradient_background(keyword, image_path)
                
            base_clip = ImageClip(image_path).with_duration(duration)
            
        # Ensure dimensions match 1080p
        if base_clip.w != VIDEO_WIDTH or base_clip.h != VIDEO_HEIGHT:
            # Resize
            base_clip = base_clip.resized((VIDEO_WIDTH, VIDEO_HEIGHT))
            
        # 2. Overlay Subtitles / Active Word Highlights
        timestamps = []
        if os.path.exists(timestamp_path):
            with open(timestamp_path, "r", encoding="utf-8") as f:
                timestamps = json.load(f)
                
        if timestamps:
            text_filter = make_subtitle_filter(timestamps)
            # Apply time filter to draw subtitles dynamically on base frames
            base_clip = base_clip.transform(text_filter)
            
        # 3. Audio Track
        # For the final segment mix, we will add the SFX overlay if triggered
        segment_audio_clip = audio_clip
        if seg.get("sfx_trigger", False) and os.path.exists(SFX_PATH):
            logger.info(f"Segment {i}: Adding transition sound effect (SFX)")
            sfx_clip = AudioFileClip(SFX_PATH).with_volume_scaled(0.5) # SFX volume at 50%
            # Combine TTS audio and SFX audio
            segment_audio_clip = CompositeAudioClip([audio_clip, sfx_clip.with_start(0)])
            
        base_clip = base_clip.with_audio(segment_audio_clip)
        video_clips.append(base_clip)
        
    if not video_clips:
        raise ValueError("No video segments were successfully compiled.")
        
    logger.info("Concatenating all segments...")
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    # 4. Background Music (BGM) with Ducking
    if os.path.exists(BGM_PATH):
        logger.info(f"Mixing background music: {BGM_PATH}")
        bgm_clip = AudioFileClip(BGM_PATH)
        # Loop BGM to match final video length
        bgm_clip = bgm_clip.with_effects([afx.AudioLoop(duration=final_video.duration)])
        # Lower BGM volume (ducking base level)
        bgm_clip = bgm_clip.with_volume_scaled(0.08)  # Set to 8% volume
        
        # Combine BGM with the video's existing speech/sfx audio track
        final_audio = CompositeAudioClip([final_video.audio, bgm_clip])
        final_video = final_video.with_audio(final_audio)
        
    # Write output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(OUTPUT_DIR, "final_video.mp4")
    
    logger.info(f"Writing final video file to {out_file}...")
    # Using low fps and libx264 fast encoding for lightweight rendering on lower-end laptops
    final_video.write_videofile(
        out_file, 
        fps=FPS, 
        codec="libx264", 
        audio_codec="aac",
        preset="ultrafast",
        threads=2
    )
    
    logger.info("Video rendering completed successfully!")
    return out_file

if __name__ == "__main__":
    logger.info("Running video renderer standalone test...")
    try:
        build_video_segments()
    except Exception as e:
        logger.error(f"Video rendering failed: {e}")
