import os
import json
import asyncio
import logging
import edge_tts

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEMP_DIR = "temp"
SCRIPT_DATA_PATH = os.path.join(TEMP_DIR, "script_data.json")
TTS_DIR = os.path.join(TEMP_DIR, "tts")

# Voice selection
# en-US-BrianNeural is a very natural and professional male voice
DEFAULT_VOICE = "en-US-BrianNeural"

async def generate_segment_tts(index: int, text: str, voice: str):
    """Generate audio and word-level timestamps for a single script segment."""
    audio_path = os.path.join(TTS_DIR, f"segment_{index}.mp3")
    timestamp_path = os.path.join(TTS_DIR, f"timestamps_{index}.json")
    
    logger.info(f"Synthesizing segment {index}: '{text[:40]}...'")
    
    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    words_data = []
    
    try:
        with open(audio_path, "wb") as fp:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    fp.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # Offset and duration are in 100-nanosecond units (1 tick = 10^-7 seconds)
                    start_time = chunk["offset"] / 10_000_000.0
                    duration = chunk["duration"] / 10_000_000.0
                    end_time = start_time + duration
                    word = chunk["text"]
                    
                    words_data.append({
                        "word": word,
                        "start": round(start_time, 3),
                        "end": round(end_time, 3)
                    })
                    
        # Save timestamps
        with open(timestamp_path, "w", encoding="utf-8") as f:
            json.dump(words_data, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Generated segment {index} audio and timestamps successfully.")
    except Exception as e:
        logger.error(f"Failed to generate TTS for segment {index}: {e}")
        raise e

async def generate_all_tts(voice=DEFAULT_VOICE):
    """Synthesize voiceover for all segments in the script."""
    if not os.path.exists(SCRIPT_DATA_PATH):
        raise FileNotFoundError(f"Script data file not found at {SCRIPT_DATA_PATH}. Please run script_generator first.")
        
    os.makedirs(TTS_DIR, exist_ok=True)
    
    with open(SCRIPT_DATA_PATH, "r", encoding="utf-8") as f:
        script_data = json.load(f)
        
    segments = script_data.get("segments", [])
    logger.info(f"Starting voiceover generation for {len(segments)} segments using voice {voice}...")
    
    # Run sequentially to prevent rate limits or stream drops
    for i, seg in enumerate(segments):
        text = seg.get("text", "")
        await generate_segment_tts(i, text, voice)
        
    logger.info("All segments TTS completed successfully.")

def format_srt_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS,mmm format for SRT."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis > 999:
        millis = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def compile_srt_subtitles(output_srt_path: str):
    """Compile individual segment word timestamps into a single, unified SRT subtitle file."""
    if not os.path.exists(SCRIPT_DATA_PATH):
        logger.error(f"Script data not found: {SCRIPT_DATA_PATH}, cannot compile SRT.")
        return
        
    with open(SCRIPT_DATA_PATH, "r", encoding="utf-8") as f:
        script_data = json.load(f)
        
    segments = script_data.get("segments", [])
    cumulative_offset = 0.0
    srt_entries = []
    srt_index = 1
    
    # Import moviepy inside to prevent circular import issues
    from moviepy import AudioFileClip
    
    logger.info("Compiling global subtitles into SRT format...")
    for i, seg in enumerate(segments):
        audio_path = os.path.join(TTS_DIR, f"segment_{i}.mp3")
        timestamp_path = os.path.join(TTS_DIR, f"timestamps_{i}.json")
        
        if not os.path.exists(audio_path):
            continue
            
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        audio_clip.close()
        
        if os.path.exists(timestamp_path):
            with open(timestamp_path, "r", encoding="utf-8") as f:
                words = json.load(f)
                
            if words:
                chunk_size = 5
                for j in range(0, len(words), chunk_size):
                    chunk = words[j:j+chunk_size]
                    if not chunk:
                        continue
                    start_time = chunk[0]["start"] + cumulative_offset
                    end_time = chunk[-1]["end"] + cumulative_offset
                    text_line = " ".join([w["word"] for w in chunk])
                    
                    srt_entries.append(
                        f"{srt_index}\n"
                        f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n"
                        f"{text_line}\n\n"
                    )
                    srt_index += 1
            else:
                text = seg.get("text", "")
                srt_entries.append(
                    f"{srt_index}\n"
                    f"{format_srt_time(cumulative_offset)} --> {format_srt_time(cumulative_offset + audio_duration)}\n"
                    f"{text}\n\n"
                )
                srt_index += 1
        else:
            text = seg.get("text", "")
            srt_entries.append(
                f"{srt_index}\n"
                f"{format_srt_time(cumulative_offset)} --> {format_srt_time(cumulative_offset + audio_duration)}\n"
                f"{text}\n\n"
            )
            srt_index += 1
            
        cumulative_offset += audio_duration
        
    os.makedirs(os.path.dirname(output_srt_path), exist_ok=True)
    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.writelines(srt_entries)
        
    logger.info(f"Successfully compiled global subtitles to: {output_srt_path}")

def run_tts():
    """Sync wrapper to execute async TTS generation."""
    asyncio.run(generate_all_tts())
    compile_srt_subtitles(os.path.join("output", "final_subtitles.srt"))

if __name__ == "__main__":
    logger.info("Running TTS generator standalone test...")
    try:
        run_tts()
    except Exception as e:
        logger.error(f"TTS generation test failed: {e}")
