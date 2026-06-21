import os
import json
import logging
from moviepy import AudioFileClip
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
TEMP_DIR = "temp"
SCRIPT_DATA_PATH = os.path.join(TEMP_DIR, "script_data.json")
TTS_DIR = os.path.join(TEMP_DIR, "tts")
ATTRIBUTIONS_PATH = os.path.join(TEMP_DIR, "footage_attributions.json")
METADATA_OUTPUT_PATH = os.path.join(TEMP_DIR, "youtube_metadata.json")

BGM_MOODS = {
    "suspenseful": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "ambient": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
    "motivational": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
    "corporate": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3"
}

def format_time(seconds: float) -> str:
    """Format seconds into MM:SS format."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def generate_youtube_metadata():
    """Generate professional YouTube video metadata (Title, Description, Tags) with chapters and credits."""
    if not os.path.exists(SCRIPT_DATA_PATH):
        raise FileNotFoundError(f"Script data not found: {SCRIPT_DATA_PATH}")

    logger.info("Reading script data...")
    with open(SCRIPT_DATA_PATH, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    title = script_data.get("title", "Geopolitical Analysis")
    base_description = script_data.get("description", "")
    tags = script_data.get("tags", [])
    music_mood = script_data.get("music_mood", "suspenseful").lower()
    segments = script_data.get("segments", [])

    # 1. Calculate Chapters based on segment audio durations
    logger.info("Calculating segment durations and YouTube chapters...")
    segment_durations = []
    for i in range(len(segments)):
        audio_path = os.path.join(TTS_DIR, f"segment_{i}.mp3")
        if os.path.exists(audio_path):
            try:
                audio_clip = AudioFileClip(audio_path)
                segment_durations.append(audio_clip.duration)
                audio_clip.close()
            except Exception as e:
                logger.warning(f"Could not read duration for segment {i}: {e}. Fallback to 10s.")
                segment_durations.append(10.0)
        else:
            logger.warning(f"Audio file not found for segment {i}: {audio_path}. Fallback to 10s.")
            segment_durations.append(10.0)

    # Setup chapter boundaries
    num_segments = len(segments)
    intro_idx = 0
    analysis_idx = max(1, int(num_segments * 0.25))
    implications_idx = max(analysis_idx + 1, int(num_segments * 0.6))
    conclusion_idx = max(implications_idx + 1, num_segments - 1 if num_segments < 4 else num_segments - 2)

    chapter_indices = {
        intro_idx: "Introduction",
        analysis_idx: "Core Analysis",
        implications_idx: "Implications & Market Impact",
        conclusion_idx: "Conclusion & Outlook"
    }

    chapters_text = []
    accumulated_time = 0.0
    for i, duration in enumerate(segment_durations):
        if i in chapter_indices:
            chapter_title = chapter_indices[i]
            chapters_text.append(f"{format_time(accumulated_time)} - {chapter_title}")
        accumulated_time += duration

    # 2. Get BGM Credit Info
    bgm_url = BGM_MOODS.get(music_mood, BGM_MOODS["suspenseful"])
    bgm_credit = f"🎵 Background Music:\n- Mood: {music_mood.capitalize()}\n- Track URL: {bgm_url}"

    # 3. Read Footage Attributions
    footage_credits = []
    if os.path.exists(ATTRIBUTIONS_PATH):
        try:
            with open(ATTRIBUTIONS_PATH, "r", encoding="utf-8") as f:
                attributions = json.load(f)
            
            # Use a dict/set to prevent duplicate credits for the same author
            unique_credits = {}
            for seg_key, data in attributions.items():
                author = data.get("author", "Unknown")
                url = data.get("url", "")
                source = data.get("source", "Stock")
                keyword = data.get("keyword", "")
                if author != "Unknown" and url:
                    unique_credits[author] = (source, url, keyword)

            if unique_credits:
                footage_credits.append("🎥 Stock Footage Credits:")
                for author, (source, url, keyword) in unique_credits.items():
                    footage_credits.append(f"- \"{keyword}\" footage by {author} ({source}): {url}")
        except Exception as e:
            logger.error(f"Failed to read footage attributions: {e}")

    # 4. Construct Final Description
    description_blocks = [
        base_description,
        "",
        "📌 TIMESTAMPS:",
        "\n".join(chapters_text),
        "",
        bgm_credit
    ]

    if footage_credits:
        description_blocks.append("")
        description_blocks.append("\n".join(footage_credits))

    # Add Hashtags
    hashtags = " ".join([f"#{t.replace(' ', '')}" for t in tags[:5]])
    description_blocks.append("")
    description_blocks.append(hashtags)

    final_description = "\n".join(description_blocks)

    # Build final metadata object
    metadata = {
        "title": title,
        "description": final_description,
        "tags": tags
    }

    # Save to file
    with open(METADATA_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    logger.info(f"YouTube metadata generated and saved to {METADATA_OUTPUT_PATH}")
    logger.info(f"Generated Description length: {len(final_description)} chars.")
    return metadata

if __name__ == "__main__":
    logger.info("Running standalone metadata generator...")
    try:
        generate_youtube_metadata()
    except Exception as e:
        logger.error(f"Metadata generation failed: {e}")
