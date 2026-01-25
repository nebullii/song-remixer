"""Music generation: instrumental + vocals combined."""

import os
import asyncio
import requests
import replicate
import edge_tts
from pydub import AudioSegment


VOICE_MAP = {
    "female": {
        "energetic": "en-US-AriaNeural",
        "melancholic": "en-US-JennyNeural",
        "dreamy": "en-GB-SoniaNeural",
        "intense": "en-US-AriaNeural",
        "hopeful": "en-US-AriaNeural",
        "nostalgic": "en-GB-SoniaNeural",
        "default": "en-US-AriaNeural",
    },
    "male": {
        "energetic": "en-US-GuyNeural",
        "melancholic": "en-GB-RyanNeural",
        "dreamy": "en-GB-RyanNeural",
        "intense": "en-US-GuyNeural",
        "hopeful": "en-US-GuyNeural",
        "nostalgic": "en-GB-RyanNeural",
        "default": "en-US-GuyNeural",
    },
    "neutral": {
        "energetic": "en-US-AriaNeural",
        "melancholic": "en-US-JennyNeural",
        "dreamy": "en-GB-SoniaNeural",
        "intense": "en-US-GuyNeural",
        "hopeful": "en-US-AriaNeural",
        "nostalgic": "en-GB-RyanNeural",
        "default": "en-US-AriaNeural",
    },
}


def _select_voice(mood: str, vocal_gender: str | None) -> str:
    gender = (vocal_gender or "neutral").lower()
    mood_key = (mood or "default").lower()
    gender_map = VOICE_MAP.get(gender, VOICE_MAP["neutral"])
    return gender_map.get(mood_key, gender_map["default"])


async def generate_vocals_async(lyrics: str, mood: str, output_path: str, vocal_gender: str | None = None):
    """Generate vocals using Edge TTS."""
    voice = _select_voice(mood, vocal_gender)

    # Clean lyrics for TTS
    clean_lyrics = lyrics.replace("[Verse 1]", "").replace("[Verse 2]", "")
    clean_lyrics = clean_lyrics.replace("[Chorus]", "").replace("[Bridge]", "")
    clean_lyrics = clean_lyrics.replace("[Outro]", "").replace("[Intro]", "")

    communicate = edge_tts.Communicate(clean_lyrics, voice, rate="-5%")
    await communicate.save(output_path)


def generate_vocals(lyrics: str, mood: str, output_path: str, vocal_gender: str | None = None):
    """Wrapper for async TTS generation."""
    asyncio.run(generate_vocals_async(lyrics, mood, output_path, vocal_gender=vocal_gender))


def generate_instrumental(style: str, title: str, duration: int = 30) -> str:
    """Generate instrumental music using Replicate's MusicGen."""
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise ValueError("REPLICATE_API_TOKEN not found. Get one at https://replicate.com/account/api-tokens")

    music_prompt = f"{style} instrumental, melodic, professional production, background music for song titled {title}"

    print(f"  Generating instrumental with MusicGen...")

    model_id = os.getenv(
        "REPLICATE_MUSICGEN_MODEL",
        "meta/musicgen:7be0f12c54a8d033a0fbd14418c9af98962da9a86f5ff7811f9b3423a1f0b7d7",
    )
    output = replicate.run(
        model_id,
        input={
            "prompt": music_prompt,
            "duration": duration,
            "model_version": "stereo-melody-large",
            "output_format": "mp3",
            "normalization_strategy": "peak"
        }
    )

    return output  # Returns URL


def mix_audio(vocals_path: str, instrumental_url: str, output_path: str):
    """Mix vocals with instrumental music."""
    print(f"  Mixing vocals with instrumental...")

    # Download instrumental
    response = requests.get(instrumental_url)
    response.raise_for_status()

    instrumental_temp = output_path.replace(".mp3", "_instrumental.mp3")
    with open(instrumental_temp, "wb") as f:
        f.write(response.content)

    # Load audio files
    vocals = AudioSegment.from_mp3(vocals_path)
    instrumental = AudioSegment.from_mp3(instrumental_temp)

    # Adjust volumes: vocals louder, instrumental as background
    vocals = vocals + 3  # Boost vocals by 3dB
    instrumental = instrumental - 6  # Lower instrumental by 6dB

    # Loop instrumental if vocals are longer
    if len(vocals) > len(instrumental):
        loops_needed = (len(vocals) // len(instrumental)) + 1
        instrumental = instrumental * loops_needed

    # Trim instrumental to match vocals length (with 2s fade out)
    instrumental = instrumental[:len(vocals) + 2000]
    instrumental = instrumental.fade_out(2000)

    # Overlay vocals on instrumental
    mixed = instrumental.overlay(vocals)

    # Export final mix
    mixed.export(output_path, format="mp3")

    # Cleanup temp files
    os.remove(instrumental_temp)
    os.remove(vocals_path)

    return output_path


def generate_and_download(
    lyrics: str,
    title: str,
    style: str = "pop",
    mood: str = "energetic",
    vocal_gender: str | None = None,
    output_dir: str = "output",
) -> str:
    """
    Generate a complete song with vocals over instrumental music.
    """
    os.makedirs(output_dir, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in title)[:50]
    safe_title = safe_title.replace(" ", "_")

    vocals_path = os.path.join(output_dir, f"{safe_title}_vocals.mp3")
    output_path = os.path.join(output_dir, f"{safe_title}.mp3")

    # Step 1: Generate vocals
    print(f"  Generating vocals...")
    generate_vocals(lyrics, mood, vocals_path, vocal_gender=vocal_gender)

    # Step 2: Generate instrumental
    instrumental_url = generate_instrumental(style, title)

    # Step 3: Mix them together
    mix_audio(vocals_path, instrumental_url, output_path)

    print(f"  Complete! Saved to {output_path}")
    return output_path
