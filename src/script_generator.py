import os
import json
import logging
from pydantic import BaseModel, Field
from typing import List
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
class ScriptSegment(BaseModel):
    text: str = Field(
        description="The spoken voiceover script text for this short segment (1-2 sentences). Must be in English, professional, engaging, and flow logically into the next segment."
    )
    visual_type: str = Field(
        description="The visual asset to show: 'footage' (Pexels stock video), 'chart' (data chart like bar or line chart), or 'map' (highlighting specific countries)."
    )
    visual_keyword: str = Field(
        description="Search keyword for stock video (e.g. 'cargo ship', 'factory', 'stock market') OR the country codes/data to display on the chart/map."
    )
    sfx_trigger: bool = Field(
        description="True if a transitional whoosh sound effect should play at the start of this segment, False otherwise. Use sparingly, only on major topic transitions."
    )

class VideoScript(BaseModel):
    title: str = Field(description="A clickbait and SEO-friendly title for the video.")
    description: str = Field(description="A short summary of the video with timestamps, credits, and hashtags.")
    tags: List[str] = Field(description="A list of 5-8 SEO tags.")
    thumbnail_text: str = Field(description="A very short, punchy, high-contrast text overlay for the YouTube thumbnail (3-5 words max, e.g. 'CHIP WAR ECLIPSES US', 'IRAN OUTLAWED?').")
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
            "segments": [
                {
                    "text": "The global semiconductor industry is facing new geopolitical tensions as superpowers race to secure advanced chip supply chains.",
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
                    "text": "However, constructing these highly advanced facilities takes years, meaning reliance on East Asia will remain high for the decade.",
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
       - Segments 1-2 (Hook/Intro): Hook the viewer with a surprising fact or key question.
       - Segments 3-5 (Core Explanation & Background): Introduce the core facts, using charts or maps to show historical context.
       - Segments 6-8 (Geopolitical/Financial Implications): Explain what this means for the global markets and future.
       - Segments 9-10 (Outro/Conclusion): Wrap up with a final takeaway or thought-provoking question, and invite viewers to subscribe.
    3. Split the script into sequential segments. Each segment must have exactly 1-2 spoken sentences.
    4. The total script should be about 8 to 12 segments (~90 to 180 seconds total).
    5. For each segment, choose the most relevant visual_type ('footage', 'chart', 'map') and assign a matching visual_keyword:
       - If 'footage': keyword must be a search term for stock video libraries (e.g. 'inflation', 'semiconductor', 'washington').
       - If 'chart': keyword must represent what data is plotted (e.g. 'inflation rate line chart', 'oil price bar chart').
       - If 'map': keyword must specify which countries/regions to highlight (e.g. 'US, China', 'Europe').
    6. Set `sfx_trigger` to true on the first segment and on major transition points (no more than 3-4 triggers in the entire video).
    7. Generate a very short, punchy `thumbnail_text` (3-5 words max) highlighting the core tension.
    8. Double check that all script claims match the source article text.
    """

    logger.info("Sending request to Gemini API (gemini-2.5-flash)...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VideoScript,
                temperature=0.3
            )
        )
        
        # Load structured JSON response
        script_dict = json.loads(response.text)
        logger.info(f"Script generated successfully. Title: '{script_dict.get('title')}'")
        
        # Save to file
        os.makedirs(TEMP_DIR, exist_ok=True)
        with open(SCRIPT_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(script_dict, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Saved script data to {SCRIPT_DATA_PATH}")
        return script_dict
    except Exception as e:
        logger.error(f"Gemini API request failed: {e}")
        raise e

if __name__ == "__main__":
    logger.info("Running script generator standalone test...")
    try:
        generate_script()
    except Exception as e:
        logger.error(f"Script generation test failed: {e}")
