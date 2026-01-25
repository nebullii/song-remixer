"""Quick song generator: Edge TTS vocals + single MusicGen instrumental."""

import os
import asyncio
import requests
import replicate
import edge_tts
from pydub import AudioSegment


MOOD_VOICES = {
    "energetic": "en-US-AriaNeural",
    "melancholic": "en-US-JennyNeural",
    "dreamy": "en-GB-SoniaNeural",
    "intense": "en-US-GuyNeural",
    "hopeful": "en-US-AriaNeural",
    "nostalgic": "en-GB-RyanNeural",
    "default": "en-US-AriaNeural"
}


def generate_quick_song(
    lyrics: str,
    title: str,
    style: str = "pop",
    mood: str = "energetic",
    output_dir: str = "output"
) -> str:
    """
    Generate a song quickly:
    - Edge TTS for vocals (~5 sec)
    - Single MusicGen instrumental (~30 sec)
    - Mix together (~1 sec)

    Total: ~40 seconds instead of 5+ minutes
    """
    os.makedirs(output_dir, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in title)[:50]
    safe_title = safe_title.replace(" ", "_")

    vocals_path = os.path.join(output_dir, f"{safe_title}_vocals.mp3")
    output_path = os.path.join(output_dir, f"{safe_title}.mp3")

    # Step 1: Generate vocals with Edge TTS (fast)
    print("  Generating vocals with Edge TTS...")
    clean_lyrics = _clean_lyrics(lyrics)
    voice = MOOD_VOICES.get(mood, MOOD_VOICES["default"])
    asyncio.run(_generate_tts(clean_lyrics, vocals_path, voice))

    # Step 2: Generate ONE instrumental track
    print("  Generating instrumental with MusicGen...")
    vocals_audio = AudioSegment.from_mp3(vocals_path)
    duration = min(30, max(10, len(vocals_audio) // 1000 + 2))

    instrumental_url = _generate_instrumental(style, title, mood, duration)

    # Step 3: Download and mix
    print("  Mixing vocals + instrumental...")
    instrumental_path = os.path.join(output_dir, f"{safe_title}_inst.mp3")
    _download_audio(instrumental_url, instrumental_path)

    _mix_audio(vocals_path, instrumental_path, output_path)

    # Cleanup temp files
    os.remove(vocals_path)
    os.remove(instrumental_path)

    print(f"  Done! Saved to {output_path}")
    return output_path


def _clean_lyrics(lyrics: str) -> str:
    """Remove section markers from lyrics."""
    import re
    # Remove [Verse], [Chorus], etc.
    clean = re.sub(r'\[.*?\]', '', lyrics)
    # Clean up extra whitespace
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    return clean.strip()


async def _generate_tts(text: str, output_path: str, voice: str):
    """Generate TTS audio."""
    communicate = edge_tts.Communicate(text, voice, rate="-5%")
    await communicate.save(output_path)


def _generate_instrumental(style: str, title: str, mood: str, duration: int) -> str:
    """Generate instrumental with MusicGen."""
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise ValueError("REPLICATE_API_TOKEN not found")

    prompt = f"{style} instrumental, {mood} mood, melodic, background music for song titled {title}"

    output = replicate.run(
        "meta/musicgen:7be0f12c54a8d033a0fbd14418c9af98962da9a86f5ff7811f9b3423a1f0b7d7",
        input={
            "prompt": prompt,
            "duration": duration,
            "model_version": "stereo-melody-large",
            "output_format": "mp3",
            "normalization_strategy": "peak"
        }
    )
    return output


def _download_audio(url: str, output_path: str):
    """Download audio from URL."""
    response = requests.get(url)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(response.content)


def _mix_audio(vocals_path: str, instrumental_path: str, output_path: str):
    """Mix vocals and instrumental."""
    vocals = AudioSegment.from_mp3(vocals_path)
    instrumental = AudioSegment.from_mp3(instrumental_path)

    # Loop instrumental if needed
    if len(instrumental) < len(vocals):
        loops = (len(vocals) // len(instrumental)) + 1
        instrumental = instrumental * loops

    # Trim to vocals length + fade
    instrumental = instrumental[:len(vocals) + 2000]
    instrumental = instrumental.fade_out(2000)

    # Mix: balanced - instrumental should be audible
    vocals = vocals + 3  # Slight vocal boost
    instrumental = instrumental - 3  # Instrumental slightly lower but still prominent

    mixed = instrumental.overlay(vocals)
    mixed.export(output_path, format="mp3")
