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
SFX_POP_PATH = os.path.join(ASSETS_DIR, "subtle_pop.wav")
SFX_PAGE_PATH = os.path.join(ASSETS_DIR, "page_flip.wav")
SFX_CLICK_PATH = os.path.join(ASSETS_DIR, "click_sound.wav")
SFX_WHOOSH_PATH = os.path.join(ASSETS_DIR, "whoosh_sfx.wav")

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 24

GEOJSON_PATH = os.path.join(ASSETS_DIR, "world.geo.json")

def wrap_text(text: str, draw: ImageDraw.Draw, font, max_width: int) -> list:
    """Helper to wrap text into multiple lines within a max width."""
    words = text.split(" ")
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        # Check text width
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
        elif hasattr(draw, "textsize"):
            w, _ = draw.textsize(test_line, font=font)
        else:
            w = len(test_line) * 15
            
        if w > max_width:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def generate_matplotlib_chart(chart_data, keyword: str, out_path: str):
    """Generate a high-quality dark-mode line or bar chart from dynamic script data."""
    logger.info(f"Generating premium chart -> {out_path}")
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 7), dpi=100)
    fig.patch.set_facecolor("#0e1017")
    ax.set_facecolor("#151821")
    
    # Configure font path
    font_path = os.path.join(ASSETS_DIR, "font.ttf")
    prop = None
    if os.path.exists(font_path):
        from matplotlib.font_manager import FontProperties
        prop = FontProperties(fname=font_path)
    
    # Setup data
    x, y = [], []
    if chart_data:
        for pt in chart_data:
            label = pt.get("label", "")
            val = pt.get("value", 0.0)
            x.append(label)
            y.append(val)
    else:
        # Fallback dummy data
        x = ["2021", "2022", "2023", "2024", "2025"]
        y = [10.0, 15.2, 8.5, 20.1, 14.0]
        
    # Decide chart type (bar chart if labels are country names/categories, line if labels are years)
    is_time_series = any(label.isdigit() or "Q" in label for label in x)
    
    if is_time_series:
        # Plot Line Chart
        ax.plot(x, y, marker='o', linewidth=4, color='#00e5ff', markersize=10, label=keyword.upper())
        ax.fill_between(x, y, color='#00e5ff', alpha=0.15)
        # Add labels to data points
        for i, val in enumerate(y):
            ax.text(x[i], val + (max(y)*0.03), f"{val}", ha="center", va="bottom", fontsize=11, fontweight="bold", color="#ffffff")
    else:
        # Plot Bar Chart
        colors = ["#ff6b6b", "#00e5ff", "#ffbe0b", "#8338ec", "#3a86c8", "#2a9d8f"][:len(x)]
        if len(colors) < len(x):
            colors = colors * 2
        bars = ax.bar(x, y, color=colors, width=0.5, edgecolor='#1e222d', linewidth=2)
        # Add labels to bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, height + (max(y)*0.02), f"{height}", ha="center", va="bottom", fontsize=11, fontweight="bold", color="#ffffff")
            
    # Hias Axes
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#2c3247')
    ax.spines['bottom'].set_color('#2c3247')
    ax.tick_params(colors='#8e9aa8', labelsize=12)
    ax.grid(True, axis='y', color='#2c3247', linestyle='--', alpha=0.5)
    
    title_text = f"DATA FIELD: {keyword.upper()}"
    ax.set_title(title_text, fontsize=18, pad=20, color='#ffffff', fontweight="bold", fontproperties=prop)
    
    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

def is_country_match(country_name: str, target_terms: list) -> bool:
    """Determine if country name matches any target terms intelligently."""
    name_lower = country_name.lower()
    normalized = [name_lower]
    
    if "united states" in name_lower:
        normalized.extend(["us", "usa", "united states of america", "washington"])
    if "iran" in name_lower:
        normalized.extend(["islamic republic of iran", "tehran"])
    if "china" in name_lower:
        normalized.extend(["prc", "people's republic of china", "beijing"])
    if "united kingdom" in name_lower:
        normalized.extend(["uk", "britain", "london"])
    if "russia" in name_lower:
        normalized.extend(["russian federation", "moscow"])
        
    for term in target_terms:
        term_clean = term.lower().strip()
        if any(term_clean in name or name in term_clean for name in normalized):
            return True
    return False

def generate_map_infographic(keyword: str, out_path: str):
    """Render a premium dark-mode world map and highlight target countries using GeoJSON."""
    logger.info(f"Generating GIS Map for '{keyword}' -> {out_path}")
    
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100) # Maintain 16:9 ratio
    fig.patch.set_facecolor("#0a0b10")
    ax.set_facecolor("#0a0b10")
    
    # Target countries split
    target_terms = [t.strip() for t in keyword.replace("and", ",").split(",")]
    
    highlighted_coords = []
    
    # Read GeoJSON
    if os.path.exists(GEOJSON_PATH):
        try:
            with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
                geojson_data = json.load(f)
                
            from matplotlib.patches import Polygon as MplPolygon
            from matplotlib.collections import PatchCollection
            
            base_patches = []
            highlight_patches = []
            
            for feature in geojson_data.get("features", []):
                country_name = feature.get("properties", {}).get("name", "")
                is_target = is_country_match(country_name, target_terms)
                
                geom = feature.get("geometry", {})
                geom_type = geom.get("type", "")
                
                polygons = []
                if geom_type == "Polygon":
                    polygons = [geom.get("coordinates", [])]
                elif geom_type == "MultiPolygon":
                    polygons = geom.get("coordinates", [])
                    
                for poly in polygons:
                    for ring in poly:
                        # Extract coordinates
                        if isinstance(ring[0][0], (int, float)):
                            pts = [(pt[0], pt[1]) for pt in ring]
                        else:
                            pts = [(pt[0], pt[1]) for pt in ring[0]]
                            
                        mpl_poly = MplPolygon(pts, closed=True)
                        if is_target:
                            highlight_patches.append(mpl_poly)
                            highlighted_coords.extend(pts)
                        else:
                            base_patches.append(mpl_poly)
                            
            # Add base countries to plot
            base_pc = PatchCollection(base_patches, facecolor='#1f2330', edgecolor='#2d3448', linewidth=0.5)
            ax.add_collection(base_pc)
            
            # Add highlighted countries
            if highlight_patches:
                hl_pc = PatchCollection(highlight_patches, facecolor='#ff4757', edgecolor='#ffffff', linewidth=1.5, alpha=0.9)
                ax.add_collection(hl_pc)
                
        except Exception as e:
            logger.error(f"Failed to render GeoJSON map: {e}")
            ax.text(0.5, 0.5, "GEOPOLITICAL WORLD MAP", ha="center", va="center", fontsize=24, color="#ff4757")
    else:
        logger.warning(f"GeoJSON map not found at {GEOJSON_PATH}. Fallback to text.")
        ax.text(0.5, 0.5, "WORLD MAP (GEOJSON MISSING)", ha="center", va="center", fontsize=24, color="#ffbe0b")
        
    # Auto Zoom Logic if target country is highlighted
    if highlighted_coords:
        x_pts = [pt[0] for pt in highlighted_coords]
        y_pts = [pt[1] for pt in highlighted_coords]
        min_x, max_x = min(x_pts), max(x_pts)
        min_y, max_y = min(y_pts), max(y_pts)
        
        width = max_x - min_x
        height = max_y - min_y
        
        margin_x = max(15.0, width * 0.45)
        margin_y = max(15.0, height * 0.45)
        
        ax.set_xlim(max(-180.0, min_x - margin_x), min(180.0, max_x + margin_x))
        ax.set_ylim(max(-60.0, min_y - margin_y), min(85.0, max_y + margin_y))
    else:
        ax.set_xlim(-180, 180)
        ax.set_ylim(-60, 85)
        
    ax.axis("off")
    
    # Add title card overlay
    font_path = os.path.join(ASSETS_DIR, "font.ttf")
    prop = None
    if os.path.exists(font_path):
        from matplotlib.font_manager import FontProperties
        prop = FontProperties(fname=font_path)
        
    title_text = f"GEOPOLITICAL ZONE: {keyword.upper()}"
    ax.text(-170, 75, title_text, color="#ffffff", fontsize=24, fontweight="bold", fontproperties=prop)
    ax.text(-170, 68, "NIMBUS INTELLIGENCE MAP SYSTEM", color="#ffbe0b", fontsize=14, fontweight="bold", fontproperties=prop)
    
    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight', pad_inches=0)
    plt.close()

def generate_news_clipping(clipping_data, out_path: str):
    """Generate a premium dark-mode newspaper clipping card with yellow highlight overlay."""
    logger.info(f"Generating news clipping -> {out_path}")
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color="#08090d")
    draw = ImageDraw.Draw(img, "RGBA")
    
    # Draw tech grid
    for x in range(0, VIDEO_WIDTH, 120):
        draw.line([(x, 0), (x, VIDEO_HEIGHT)], fill="#11131c", width=1)
    for y in range(0, VIDEO_HEIGHT, 120):
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill="#11131c", width=1)
        
    # Draw central paper background
    paper_x1, paper_y1 = 200, 150
    paper_x2, paper_y2 = VIDEO_WIDTH - 200, VIDEO_HEIGHT - 150
    draw.rectangle([(paper_x1, paper_y1), (paper_x2, paper_y2)], fill=(18, 20, 29, 255), outline=(0, 229, 255, 60), width=3)
    
    # Load fonts
    font_path = os.path.join(ASSETS_DIR, "font.ttf")
    try:
        if os.path.exists(font_path):
            source_font = ImageFont.truetype(font_path, 28)
            headline_font = ImageFont.truetype(font_path, 48)
            body_font = ImageFont.truetype(font_path, 32)
        else:
            source_font = ImageFont.truetype("arial.ttf", 28)
            headline_font = ImageFont.truetype("arial.ttf", 48)
            body_font = ImageFont.truetype("arial.ttf", 32)
    except IOError:
        source_font = ImageFont.load_default()
        headline_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        
    # Setup data
    source_name = "REUTERS"
    headline = "Tensions Rise Amid Trade Disputes"
    highlight_text = "Negotiators are warning that unresolved issues could lead to an immediate deadlock."
    
    if clipping_data:
        source_name = clipping_data.get("source_name", source_name).upper()
        headline = clipping_data.get("headline", headline)
        highlight_text = clipping_data.get("highlight_text", highlight_text)
        
    # Draw Source Header
    draw.text((250, 190), f"⚡ {source_name}", fill="#00e5ff", font=source_font)
    draw.line([(250, 240), (VIDEO_WIDTH - 250, 240)], fill="#2c3247", width=2)
    
    # Draw Headline
    headline_lines = wrap_text(headline, draw, headline_font, VIDEO_WIDTH - 500)
    curr_y = 280
    for line in headline_lines:
        draw.text((250, curr_y), line, fill="#ffffff", font=headline_font)
        curr_y += 65
        
    draw.line([(250, curr_y + 15), (VIDEO_WIDTH - 250, curr_y + 15)], fill="#2c3247", width=2)
    curr_y += 50
    
    # Draw Highlighted Body Text
    body_lines = wrap_text(highlight_text, draw, body_font, VIDEO_WIDTH - 500)
    for line in body_lines:
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), line, font=body_font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]
        elif hasattr(draw, "textsize"):
            line_w, line_h = draw.textsize(line, font=body_font)
        else:
            line_w, line_h = len(line) * 16, 32
            
        # Draw translucent yellow highlighter box
        draw.rectangle(
            [(245, curr_y - 2), (255 + line_w, curr_y + line_h + 8)], 
            fill=(255, 235, 59, 90)
        )
        draw.text((250, curr_y), line, fill="#ffffff", font=body_font)
        curr_y += 50
        
    img.save(out_path)

def generate_quote_card(quote_data, out_path: str):
    """Generate a premium quote card with large quote marks and author credits."""
    logger.info(f"Generating quote card -> {out_path}")
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color="#08090d")
    draw = ImageDraw.Draw(img, "RGBA")
    
    draw.rectangle([(50, 50), (VIDEO_WIDTH - 50, VIDEO_HEIGHT - 50)], outline="#1e2230", width=2)
    
    # Fonts
    font_path = os.path.join(ASSETS_DIR, "font.ttf")
    try:
        if os.path.exists(font_path):
            quote_font = ImageFont.truetype(font_path, 42)
            author_font = ImageFont.truetype(font_path, 34)
            title_font = ImageFont.truetype(font_path, 26)
            bg_quote_font = ImageFont.truetype(font_path, 180)
        else:
            quote_font = ImageFont.truetype("arial.ttf", 42)
            author_font = ImageFont.truetype("arial.ttf", 34)
            title_font = ImageFont.truetype("arial.ttf", 26)
            bg_quote_font = ImageFont.truetype("arial.ttf", 180)
    except IOError:
        quote_font = author_font = title_font = bg_quote_font = ImageFont.load_default()
        
    # Setup data
    author = "JOHN DOE"
    author_title = "Global Market Analyst"
    quote_text = "The future belongs to those who prepare for the geopolitical realignments happening today."
    
    if quote_data:
        author = quote_data.get("author", author).upper()
        author_title = quote_data.get("author_title", author_title)
        quote_text = quote_data.get("quote_text", quote_text)
        
    # Draw giant quote mark
    draw.text((150, 180), "“", fill=(0, 229, 255, 30), font=bg_quote_font)
    
    # Draw Quote Body Text
    quote_lines = wrap_text(f'"{quote_text}"', draw, quote_font, VIDEO_WIDTH - 400)
    curr_y = 350
    for line in quote_lines:
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), line, font=quote_font)
            w = bbox[2] - bbox[0]
        else:
            w = len(line) * 20
        x = (VIDEO_WIDTH - w) // 2
        draw.text((x, curr_y), line, fill="#ffffff", font=quote_font)
        curr_y += 60
        
    # Separator
    draw.line([(VIDEO_WIDTH//2 - 150, curr_y + 30), (VIDEO_WIDTH//2 + 150, curr_y + 30)], fill="#00e5ff", width=3)
    curr_y += 65
    
    # Author
    if hasattr(draw, "textbbox"):
        bbox = draw.textbbox((0, 0), author, font=author_font)
        w = bbox[2] - bbox[0]
    else:
        w = len(author) * 18
    draw.text(((VIDEO_WIDTH - w)//2, curr_y), author, fill="#ffbe0b", font=author_font)
    curr_y += 48
    
    # Title
    if hasattr(draw, "textbbox"):
        bbox = draw.textbbox((0, 0), author_title, font=title_font)
        w = bbox[2] - bbox[0]
    else:
        w = len(author_title) * 13
    draw.text(((VIDEO_WIDTH - w)//2, curr_y), author_title, fill="#889ab0", font=title_font)
    
    img.save(out_path)

def generate_stat_card(stat_data, out_path: str):
    """Generate a premium stats card highlighting a big number."""
    logger.info(f"Generating stat card -> {out_path}")
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color="#08090d")
    draw = ImageDraw.Draw(img, "RGBA")
    
    for x in range(0, VIDEO_WIDTH, 150):
        draw.line([(x, 0), (x, VIDEO_HEIGHT)], fill="#11131a", width=1)
    for y in range(0, VIDEO_HEIGHT, 150):
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill="#11131a", width=1)
        
    # Fonts
    font_path = os.path.join(ASSETS_DIR, "font.ttf")
    try:
        if os.path.exists(font_path):
            big_font = ImageFont.truetype(font_path, 160)
            label_font = ImageFont.truetype(font_path, 38)
            system_font = ImageFont.truetype(font_path, 22)
        else:
            big_font = ImageFont.truetype("arial.ttf", 160)
            label_font = ImageFont.truetype("arial.ttf", 38)
            system_font = ImageFont.truetype("arial.ttf", 22)
    except IOError:
        big_font = label_font = system_font = ImageFont.load_default()
        
    # Setup data
    val = "4,200+"
    label = "Active Trade Restrictions Globally"
    
    if stat_data:
        val = stat_data.get("stat_value", val)
        label = stat_data.get("stat_label", label)
        
    draw.text((100, 100), "⚡ STATISTICAL METRIC DATA", fill="#889ab0", font=system_font)
    draw.line([(100, 140), (450, 140)], fill="#00e5ff", width=2)
    
    # Centered Big Number
    if hasattr(draw, "textbbox"):
        bbox = draw.textbbox((0, 0), val, font=big_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    else:
        w, h = len(val) * 75, 140
    num_x = (VIDEO_WIDTH - w) // 2
    num_y = (VIDEO_HEIGHT - h) // 2 - 50
    
    draw.rectangle([(num_x - 30, num_y - 20), (num_x + w + 30, num_y + h + 40)], fill=(0, 229, 255, 15), outline=(0, 229, 255, 45), width=2)
    draw.text((num_x, num_y), val, fill="#ff4757", font=big_font)
    
    # Centered Label below
    label_lines = wrap_text(label, draw, label_font, VIDEO_WIDTH - 400)
    curr_y = num_y + h + 80
    for line in label_lines:
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), line, font=label_font)
            w = bbox[2] - bbox[0]
        else:
            w = len(line) * 18
        x = (VIDEO_WIDTH - w) // 2
        draw.text((x, curr_y), line, fill="#ffffff", font=label_font)
        curr_y += 50
        
    img.save(out_path)

def generate_timeline(timeline_data, out_path: str):
    """Generate a horizontal timeline chronology infographic path."""
    logger.info(f"Generating timeline -> {out_path}")
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color="#08090d")
    draw = ImageDraw.Draw(img, "RGBA")
    
    # Fonts
    font_path = os.path.join(ASSETS_DIR, "font.ttf")
    try:
        if os.path.exists(font_path):
            title_font = ImageFont.truetype(font_path, 36)
            year_font = ImageFont.truetype(font_path, 34)
            desc_font = ImageFont.truetype(font_path, 22)
        else:
            title_font = ImageFont.truetype("arial.ttf", 36)
            year_font = ImageFont.truetype("arial.ttf", 34)
            desc_font = ImageFont.truetype("arial.ttf", 22)
    except IOError:
        title_font = year_font = desc_font = ImageFont.load_default()
        
    # Setup data
    events = [
        {"time_label": "2015", "event_description": "Nuclear Deal Signed"},
        {"time_label": "2018", "event_description": "US Withdraws"},
        {"time_label": "2020", "event_description": "Crippling Sanctions"},
        {"time_label": "2026", "event_description": "Present Talks"}
    ]
    
    if timeline_data:
        events = timeline_data
        
    draw.text((100, 100), "📅 CHRONOLOGICAL TIMELINE", fill="#00e5ff", font=title_font)
    
    line_y = 520
    draw.line([(150, line_y), (VIDEO_WIDTH - 150, line_y)], fill="#2c3247", width=6)
    
    num_events = len(events)
    spacing = (VIDEO_WIDTH - 300) / max(1, num_events - 1)
    
    for i, event in enumerate(events):
        x = 150 + int(i * spacing)
        
        # Node
        draw.ellipse([(x - 20, line_y - 20), (x + 20, line_y + 20)], fill=(8, 9, 13, 255), outline="#00e5ff", width=4)
        draw.ellipse([(x - 8, line_y - 8), (x + 8, line_y + 8)], fill="#ffbe0b")
        
        # Label above
        year = event.get("time_label", "")
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), year, font=year_font)
            w = bbox[2] - bbox[0]
        else:
            w = len(year) * 16
            
        text_x = x - w//2
        if text_x < 50:
            text_x = 50
        elif text_x + w > VIDEO_WIDTH - 50:
            text_x = VIDEO_WIDTH - 50 - w
        draw.text((text_x, line_y - 80), year, fill="#ffbe0b", font=year_font)
        
        # Desc below
        desc = event.get("event_description", "")
        desc_lines = wrap_text(desc, draw, desc_font, int(spacing - 20))
        curr_y = line_y + 40
        for line in desc_lines:
            if hasattr(draw, "textbbox"):
                bbox = draw.textbbox((0, 0), line, font=desc_font)
                w = bbox[2] - bbox[0]
            else:
                w = len(line) * 10
                
            text_x = x - w//2
            if text_x < 50:
                text_x = 50
            elif text_x + w > VIDEO_WIDTH - 50:
                text_x = VIDEO_WIDTH - 50 - w
                
            draw.text((text_x, curr_y), line, fill="#ffffff", font=desc_font)
            curr_y += 30
            
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
            left, top, right, bottom = draw.textbbox((0, 0), active_word, font=font)
            w = right - left
            h = bottom - top
            x = (VIDEO_WIDTH - w) // 2
            y = VIDEO_HEIGHT - 220
            text_x = x - left
            text_y = y - top
        elif hasattr(draw, "textsize"):
            w, h = draw.textsize(active_word, font=font)
            x = (VIDEO_WIDTH - w) // 2
            y = VIDEO_HEIGHT - 220
            text_x, text_y = x, y
        else:
            w, h = len(active_word) * 35, 70
            x = (VIDEO_WIDTH - w) // 2
            y = VIDEO_HEIGHT - 220
            text_x, text_y = x, y
            
        # Draw background card for text readability
        draw.rectangle([(x-20, y-10), (x+w+20, y+h+10)], fill=(0, 0, 0, 180))
        
        # Draw text with outline
        draw.text((text_x, text_y), active_word, fill="#ffeb3b", font=font)  # Bright yellow highlighted word
        
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
                generate_matplotlib_chart(seg.get("chart_data"), keyword, image_path)
            elif visual_type == "map":
                generate_map_infographic(keyword, image_path)
            elif visual_type == "clipping":
                generate_news_clipping(seg.get("clipping_data"), image_path)
            elif visual_type == "quote":
                generate_quote_card(seg.get("quote_data"), image_path)
            elif visual_type == "stat":
                generate_stat_card(seg.get("stat_data"), image_path)
            elif visual_type == "timeline":
                generate_timeline(seg.get("timeline_data"), image_path)
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
        if seg.get("sfx_trigger", False):
            # Select sound effect based on visual type with fallback
            if visual_type in ["chart", "map"]:
                current_sfx_path = SFX_POP_PATH if os.path.exists(SFX_POP_PATH) else SFX_PATH
            elif visual_type == "clipping":
                current_sfx_path = SFX_PAGE_PATH if os.path.exists(SFX_PAGE_PATH) else SFX_PATH
            elif visual_type == "quote":
                current_sfx_path = SFX_CLICK_PATH if os.path.exists(SFX_CLICK_PATH) else SFX_PATH
            elif visual_type == "stat":
                current_sfx_path = SFX_WHOOSH_PATH if os.path.exists(SFX_WHOOSH_PATH) else SFX_PATH
            else:
                current_sfx_path = SFX_PATH

            if os.path.exists(current_sfx_path):
                logger.info(f"Segment {i}: Adding transition sound effect (SFX) from {current_sfx_path} for visual type '{visual_type}'")
                sfx_clip = AudioFileClip(current_sfx_path).with_volume_scaled(0.5) # SFX volume at 50%
                # Combine TTS audio and SFX audio
                segment_audio_clip = CompositeAudioClip([audio_clip, sfx_clip.with_start(0)])
            else:
                logger.warning(f"Segment {i}: SFX triggered but file not found: {current_sfx_path}")
            
        base_clip = base_clip.with_audio(segment_audio_clip)
        video_clips.append(base_clip)
        
    if not video_clips:
        raise ValueError("No video segments were successfully compiled.")
        
    logger.info("Concatenating all segments...")
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    # 4. Background Music (BGM) with Ducking
    music_mood = script_data.get("music_mood", "suspenseful")
    mood_bgm_path = os.path.join(ASSETS_DIR, f"bgm_{music_mood}.mp3")
    target_bgm_path = mood_bgm_path if os.path.exists(mood_bgm_path) else BGM_PATH
    
    if os.path.exists(target_bgm_path):
        logger.info(f"Mixing background music: {target_bgm_path} (mood: {music_mood})")
        bgm_clip = AudioFileClip(target_bgm_path)
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
