"""Text-to-speech generation for songs."""

import asyncio
import os
from pathlib import Path

import edge_tts


MOOD_VOICES = {
    "energetic": "en-US-AriaNeural",
    "melancholic": "en-US-JennyNeural",
    "dreamy": "en-GB-SoniaNeural",
    "intense": "en-US-GuyNeural",
    "hopeful": "en-US-AriaNeural",
    "nostalgic": "en-GB-RyanNeural",
    "default": "en-US-AriaNeural"
}

MOOD_RATE = {
    "energetic": "+10%",
    "melancholic": "-15%",
    "dreamy": "-10%",
    "intense": "+5%",
    "hopeful": "+0%",
    "nostalgic": "-5%",
    "default": "+0%"
}


async def _generate_speech(text: str, output_path: str, voice: str, rate: str) -> str:
    """Internal async function to generate speech."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)
    return output_path


def generate_song_audio(song: dict, output_dir: str = "output") -> str:
    """Generate audio file for a song."""
    Path(output_dir).mkdir(exist_ok=True)

    mood = song.get("mood", "default")
    voice = MOOD_VOICES.get(mood, MOOD_VOICES["default"])
    rate = MOOD_RATE.get(mood, MOOD_RATE["default"])

    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in song["title"])
    safe_title = safe_title.replace(" ", "_")[:50]
    output_path = os.path.join(output_dir, f"{safe_title}.mp3")

    lyrics = prepare_lyrics_for_tts(song["lyrics"])
    asyncio.run(_generate_speech(lyrics, output_path, voice, rate))

    return output_path


def prepare_lyrics_for_tts(lyrics: str) -> str:
    """Prepare lyrics for better TTS output."""
    lines = lyrics.split('\n')
    processed = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            processed.append(f"... {stripped[1:-1]} ...")
        elif not stripped:
            processed.append("...")
        else:
            processed.append(stripped)

    return '\n'.join(processed)
