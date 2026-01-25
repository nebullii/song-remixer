"""Music generation using Suno AI."""

import os
import time
from suno import Suno


def get_suno_client() -> Suno:
    """Initialize Suno client."""
    cookie = os.getenv("SUNO_COOKIE")
    if not cookie:
        raise ValueError("SUNO_COOKIE not found in environment. Get it from suno.ai browser cookies.")
    return Suno(cookie=cookie)


def generate_song(lyrics: str, title: str, style: str = "pop", wait: bool = True) -> dict:
    """
    Generate a song using Suno AI.

    Args:
        lyrics: The song lyrics
        title: Song title
        style: Music style/genre tags (e.g., "pop, energetic, 80s")
        wait: Wait for audio generation to complete

    Returns:
        dict with song info and audio URL
    """
    client = get_suno_client()

    # Check credits first
    credits = client.get_credits()
    print(f"  Suno credits: {credits.credits_left} remaining")

    if credits.credits_left < 10:
        raise ValueError("Not enough Suno credits. Each song costs ~10 credits.")

    # Generate the song
    clips = client.generate(
        prompt=lyrics,
        is_custom=True,  # We're providing custom lyrics
        tags=style,
        title=title,
        make_instrumental=False,
        wait_audio=wait
    )

    if not clips:
        raise ValueError("No songs generated")

    clip = clips[0]

    return {
        "id": clip.id,
        "title": clip.title,
        "audio_url": clip.audio_url,
        "image_url": clip.image_url,
        "duration": clip.duration,
        "status": clip.status
    }


def download_song(song: dict, output_dir: str = "output") -> str:
    """Download the generated song."""
    client = get_suno_client()

    os.makedirs(output_dir, exist_ok=True)

    # Download using Suno client
    path = client.download(song["id"], path=output_dir)
    return path


def generate_and_download(lyrics: str, title: str, style: str = "pop", output_dir: str = "output") -> str:
    """Generate a song and download it."""
    print(f"  Generating song with Suno AI...")

    song = generate_song(lyrics, title, style, wait=True)

    print(f"  Song generated: {song['title']}")
    print(f"  Downloading...")

    path = download_song(song, output_dir)

    return path
