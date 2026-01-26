"""Simplified song generation - Claude (lyrics) + MiniMax (music+vocals)."""

import os
import hashlib
import requests
import replicate
import anthropic


def _get_cache_path(artist: str, song: str, style: str, output_dir: str) -> str:
    """Generate a cache key based on inputs."""
    key = f"{artist}_{song}_{style}".lower()
    hash_key = hashlib.md5(key.encode()).hexdigest()[:12]
    return os.path.join(output_dir, f"cache_{hash_key}.mp3")


def generate_lyrics_fast(artist: str, song: str, style: str) -> tuple[str, str]:
    """Generate lyrics quickly with Claude. Returns (title, lyrics)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found")

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Write short song lyrics (under 400 chars) inspired by "{song}" by {artist}. Style: {style}.

Format:
TITLE: [catchy title]

[Verse]
(4 lines)

[Chorus]
(4 lines)

Keep it SHORT. Under 400 characters total for lyrics."""
        }]
    )

    text = response.content[0].text
    lines = text.strip().split('\n')

    title = f"{song} Remix"
    lyrics_start = 0

    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.strip().startswith("["):
            lyrics_start = i
            break

    lyrics = '\n'.join(lines[lyrics_start:]).strip()

    # Ensure under 400 chars for MiniMax
    if len(lyrics) > 400:
        lyrics = lyrics[:400].rsplit('\n', 1)[0]

    return title, lyrics


def generate_song_suno(
    artist: str,
    album: str,
    style: str = "pop",
    output_dir: str = "output"
) -> dict:
    """
    Generate a complete song: Claude (lyrics) + MiniMax (music+vocals).

    2 API calls total. Skips Genius entirely.

    Returns:
        dict with 'audio_path', 'title', 'lyrics'
    """
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise ValueError("REPLICATE_API_TOKEN not found")

    os.makedirs(output_dir, exist_ok=True)

    # Check cache first
    cache_path = _get_cache_path(artist, album, style, output_dir)
    if os.path.exists(cache_path):
        print(f"  Using cached song!")
        return {
            "audio_path": cache_path,
            "title": f"{album} Remix",
            "lyrics": "(cached)",
        }

    # Step 1: Generate lyrics with Claude (~3 sec)
    print(f"  Generating lyrics with Claude...")
    title, lyrics = generate_lyrics_fast(artist, album, style)
    print(f"  Generated: {title}")

    # Step 2: Generate music with MiniMax music-1.5 (better quality, up to 4 min)
    print(f"  Generating music with MiniMax...")

    prompt = f"{style}, professional production, catchy melody, inspired by {artist}"

    output = replicate.run(
        "minimax/music-1.5",
        input={
            "prompt": prompt,
            "lyrics": lyrics,
            "audio_format": "mp3",
        }
    )

    # Handle output
    audio_url = None
    if isinstance(output, str):
        audio_url = output
    elif hasattr(output, 'url'):
        audio_url = output.url
    elif hasattr(output, 'read'):
        audio_url = output

    if not audio_url:
        raise ValueError(f"No audio URL in MiniMax output: {output}")

    # Download
    print(f"  Downloading...")
    if isinstance(audio_url, str):
        response = requests.get(audio_url)
        response.raise_for_status()
        audio_content = response.content
    else:
        audio_content = audio_url.read()

    # Save to cache path
    with open(cache_path, "wb") as f:
        f.write(audio_content)

    print(f"  Complete! Saved to {cache_path}")

    return {
        "audio_path": cache_path,
        "title": title,
        "lyrics": lyrics,
    }
