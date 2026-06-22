import os
import json
import logging
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Input/Output paths
TEMP_DIR = "temp"
NEWS_DATA_PATH = os.path.join(TEMP_DIR, "news_data.json")
SCRIPT_DATA_PATH = os.path.join(TEMP_DIR, "script_data.json")

# Define Pydantic Schema for Structured Output
class ChartPoint(BaseModel):
    label: str = Field(description="The X-axis label (e.g. '2021', 'US', 'Q1').")
    value: float = Field(description="The Y-axis numeric value.")

class ClippingData(BaseModel):
    source_name: str = Field(description="The name of the news source (e.g. 'Financial Times', 'Bloomberg', 'Reuters').")
    headline: str = Field(description="A realistic news article headline related to this segment.")
    highlight_text: str = Field(description="A key sentence from the simulated article body to be highlighted with a yellow marker.")

class QuoteData(BaseModel):
    author: str = Field(description="The name of the public figure being quoted (e.g. 'Jerome Powell', 'Joe Biden').")
    author_title: str = Field(description="Their official title or role (e.g. 'Fed Chairman', 'US President').")
    quote_text: str = Field(description="The exact or realistic quote text related to the segment content.")

class StatData(BaseModel):
    stat_value: str = Field(description="The prominent big number or metric value (e.g. '$85.40', '4,200+', '-15%').")
    stat_label: str = Field(description="A short label describing what this metric represents (e.g. 'Oil Price per Barrel', 'New Sanctions').")

class TimelineEvent(BaseModel):
    time_label: str = Field(description="The year or time marker (e.g. '2015', '2018', 'Present').")
    event_description: str = Field(description="A brief description of what occurred (3-6 words max).")

class ScriptSegment(BaseModel):
    text: str = Field(
        description="The spoken voiceover script text for this short segment (1-2 sentences). Must be in English, professional, engaging, and flow logically into the next segment."
    )
    visual_type: str = Field(
        description="The visual asset to show. MUST be one of: "
                    "'footage' (Pexels stock video), "
                    "'chart' (matplotlib data chart), "
                    "'map' (highlighted GIS world map), "
                    "'clipping' (newspaper headline clipping), "
                    "'quote' (quote card of a public figure), "
                    "'stat' (big number/metric card), "
                    "or 'timeline' (chronology timeline)."
    )
    visual_keyword: str = Field(
        description="Search keyword for stock video OR target countries/terms to highlight/label."
    )
    sfx_trigger: bool = Field(
        description="True if a transitional whoosh or click sound effect should play at the start of this segment, False otherwise. Use sparingly, only on major topic transitions."
    )
    
    # Optional parameters depending on visual_type
    chart_data: Optional[List[ChartPoint]] = Field(default=None, description="Required only if visual_type is 'chart'. Provide 4-6 data points.")
    clipping_data: Optional[ClippingData] = Field(default=None, description="Required only if visual_type is 'clipping'.")
    quote_data: Optional[QuoteData] = Field(default=None, description="Required only if visual_type is 'quote'.")
    stat_data: Optional[StatData] = Field(default=None, description="Required only if visual_type is 'stat'.")
    timeline_data: Optional[List[TimelineEvent]] = Field(default=None, description="Required only if visual_type is 'timeline'. Provide 3-4 chronological events.")

class VideoScript(BaseModel):
    title: str = Field(description="A clickbait and SEO-friendly title for the video.")
    description: str = Field(description="A short summary of the video with timestamps, credits, and hashtags.")
    tags: List[str] = Field(description="A list of 5-8 SEO tags.")
    thumbnail_text: str = Field(description="A very short, punchy, high-contrast text overlay for the YouTube thumbnail (3-5 words max, e.g. 'CHIP WAR ECLIPSES US', 'IRAN OUTLAWED?').")
    music_mood: str = Field(description="The background music mood for the video. MUST be one of: 'suspenseful', 'ambient', 'motivational', or 'corporate'.")
    segments: List[ScriptSegment] = Field(description="The sequential segments of the video. The total script should contain 8-12 segments for a 1-2 minute video.")

def generate_script() -> dict:
    """Generate a structured script from news data using Gemini API."""
    if not os.path.exists(NEWS_DATA_PATH):
        raise FileNotFoundError(f"News data file not found at {NEWS_DATA_PATH}. Please run news_sourcer first.")

    logger.info(f"Reading news data from {NEWS_DATA_PATH}...")
    with open(NEWS_DATA_PATH, "r", encoding="utf-8") as f:
        news_data = json.load(f)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "" or "your_gemini_api_key" in api_key:
        logger.warning("GEMINI_API_KEY not configured. Generating a high-quality mock script for testing.")
        mock_script = {
            "title": "The Global Chip War Escalates",
            "description": "An analysis of the global semiconductor supply chain tensions and domestic chip building efforts in the US and Europe. #Geopolitics #Chips #Tech",
            "tags": ["geopolitics", "semiconductors", "chip war", "supply chain", "finance", "technology"],
            "thumbnail_text": "CHIP WAR ESCALATES",
            "music_mood": "suspenseful",
            "segments": [
                {
                    "text": "This is The Strategic Brief — here's what you need to know about the escalating global chip war, and why it matters.",
                    "visual_type": "footage",
                    "visual_keyword": "semiconductor",
                    "sfx_trigger": True
                },
                {
                    "text": "A comparison of global chip production highlights Taiwan's massive dominance, manufacturing over ninety percent of advanced chips.",
                    "visual_type": "chart",
                    "visual_keyword": "Taiwan semiconductor market share",
                    "sfx_trigger": False
                },
                {
                    "text": "New government subsidies in the United States and Europe aim to construct local fabrication plants to counter this vulnerability.",
                    "visual_type": "map",
                    "visual_keyword": "United States, Germany",
                    "sfx_trigger": True
                },
                {
                    "text": "That's today's brief. If you want to stay ahead of the stories shaping global power and markets, subscribe to The Strategic Brief.",
                    "visual_type": "footage",
                    "visual_keyword": "cleanroom factory",
                    "sfx_trigger": False
                }
            ]
        }
        os.makedirs(TEMP_DIR, exist_ok=True)
        with open(SCRIPT_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(mock_script, f, indent=4, ensure_ascii=False)
        logger.info(f"Saved mock script data to {SCRIPT_DATA_PATH}")
        return mock_script

    logger.info("Initializing Gemini API Client...")
    client = genai.Client(api_key=api_key)

    # Prompt design for grounding
    prompt = f"""
    You are an expert geopolitical and finance video scriptwriter. Your goal is to write a highly engaging and educational video script based ONLY on the facts provided in the source article below. Do not invent new facts, make ungrounded claims, or exaggerate.

    Source Article Title: {news_data.get('title', 'Geopolitical News')}
    Source Article Content:
    {news_data.get('text', '')}

    Instructions:
    1. The script must be in English, professional, analytical, and write in an engaging documentary storytelling style (similar to Vox, Johnny Harris, or Economics Explained).
    2. The script MUST follow a clear narrative structure:
       - Segment 1 (Signature Opener): Choose one of these signature openers, replacing [topic] with the main subject of the news (e.g. "the global chip war", "sanctions on Iran"):
         * "This is The Strategic Brief — here's what you need to know about [topic], and why it matters."
         * "Welcome to The Strategic Brief. Today, we're unpacking [topic], and what it means for the global order."
         * "You're listening to The Strategic Brief — here is the story behind [topic], and why you should pay attention."
         * "On today's Strategic Brief: we dive into [topic] and why this development matters right now."
         Please select the opener that best fits the article.
       - Segments 2-3 (Hook/Intro continued): Hook the viewer further with a surprising fact or key question.
       - Segments 4-6 (Core Explanation & Background): Introduce the core facts, using charts or maps to show historical context.
       - Segments 7-8 (Geopolitical/Financial Implications): Explain what this means for the global markets and future.
       - Last Segment (Signature Outro & CTA): Choose one of these signature outros to encourage subscriptions:
         * "That's today's brief. If you want to stay ahead of the stories shaping global power and markets, subscribe to The Strategic Brief."
         * "That concludes today's brief. To make sure you don't miss the next story shaping global finance and power, subscribe to The Strategic Brief."
         * "And that's the brief for today. If you want to stay informed on the geopolitical forces driving global markets, hit subscribe to The Strategic Brief."
         * "Thank you for listening to today's brief. Subscribe to The Strategic Brief to keep your finger on the pulse of global power and market dynamics."
         Please select the outro that best matches the final tone of the video.
    3. Split the script into sequential segments. Each segment must have exactly 1-2 spoken sentences.
    4. The total script should be about 8 to 12 segments (~90 to 180 seconds total).
    5. For each segment, choose the most relevant visual_type ('footage', 'chart', 'map', 'clipping', 'quote', 'stat', 'timeline') and assign a matching visual_keyword:
       - If 'footage': keyword must be a search term for stock video libraries (e.g. 'inflation', 'semiconductor', 'washington'). First and last segments must be 'footage'.
       - If 'chart': you MUST supply `chart_data` (4-6 realistic data points extracted from the article context).
       - If 'map': keyword must specify which countries/regions to highlight (e.g. 'US, China', 'Europe').
       - If 'clipping': you MUST supply `clipping_data` (realistic headline, news source, and body highlight text).
       - If 'quote': you MUST supply `quote_data` (famous quote or realistic statement from a key figure).
       - If 'stat': you MUST supply `stat_data` (a big number and a short label).
       - If 'timeline': you MUST supply `timeline_data` (3-4 chronological timeline events).
       - Note: Use a diverse mix of visual types across the segments to keep the video highly dynamic and visually engaging!
       - Note: Do NOT use the same visual_type in consecutive segments if possible.
    6. Set `sfx_trigger` to true on the first segment and on major transition points (no more than 3-4 triggers in the entire video).
    7. Generate a very short, punchy `thumbnail_text` (3-5 words max) highlighting the core tension.
    8. Select the most appropriate background music mood for the video: 'suspenseful' (for trade/tech wars, conflict, geopolitical tension), 'ambient' (for neutral analysis, background, geography), 'motivational' (for growth, innovation, economic rise), or 'corporate' (for financial policies, business news).
    9. Double check that all script claims match the source article text.
    """

    models_to_try = ["gemini-3.5-flash", "gemini-3.1-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"]
    response = None
    last_error = None
    selected_model = None
    
    for model_name in models_to_try:
        logger.info(f"Sending request to Gemini API using model: '{model_name}'...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VideoScript,
                    temperature=0.3
                )
            )
            selected_model = model_name
            break
        except Exception as e:
            logger.warning(f"Failed with model '{model_name}': {e}. Trying fallback...")
            last_error = e
            
    if response is None:
        logger.error("All Gemini API models failed.")
        raise last_error
        
    try:
        # Load structured JSON response
        script_dict = json.loads(response.text)
        logger.info(f"Script generated successfully using model '{selected_model}'. Title: '{script_dict.get('title')}'")
        
        # Save to file
        os.makedirs(TEMP_DIR, exist_ok=True)
        with open(SCRIPT_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(script_dict, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Saved script data to {SCRIPT_DATA_PATH}")
        return script_dict
    except Exception as e:
        logger.error(f"Failed to parse or save script: {e}")
        raise e

if __name__ == "__main__":
    logger.info("Running script generator standalone test...")
    try:
        generate_script()
    except Exception as e:
        logger.error(f"Script generation test failed: {e}")
