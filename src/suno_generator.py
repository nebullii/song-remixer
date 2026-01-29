"""Simplified song generation - Claude (lyrics) + MiniMax (music+vocals)."""

import os
import json
import hashlib
import requests
import replicate
import anthropic


# Cache index file to map hash -> metadata (title, genre, filename)
CACHE_INDEX_FILE = "cache_index.json"


def _get_cache_hash(artist: str, song: str, style: str) -> str:
    """Generate a short hash for cache lookup."""
    key = f"{artist}_{song}_{style}".lower()
    return hashlib.md5(key.encode()).hexdigest()[:8]


def _sanitize_filename(name: str) -> str:
    """Convert a title to a safe filename."""
    import re
    # Replace spaces with underscores, remove special chars
    safe = re.sub(r'[^\w\s-]', '', name)
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe[:50]  # Limit length


def _load_cache_index(output_dir: str) -> dict:
    """Load the cache index mapping hash -> metadata."""
    index_path = os.path.join(output_dir, CACHE_INDEX_FILE)
    if os.path.exists(index_path):
        try:
            with open(index_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache_index(output_dir: str, index: dict):
    """Save the cache index."""
    index_path = os.path.join(output_dir, CACHE_INDEX_FILE)
    try:
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save cache index: {e}")


def _get_cached_song(artist: str, song: str, style: str, output_dir: str) -> dict | None:
    """Check if song is cached. Returns metadata if found, None otherwise."""
    hash_key = _get_cache_hash(artist, song, style)
    index = _load_cache_index(output_dir)

    if hash_key in index:
        entry = index[hash_key]
        audio_path = os.path.join(output_dir, entry["filename"])
        if os.path.exists(audio_path):
            return {
                "audio_path": audio_path,
                "title": entry["title"],
                "genre": entry["genre"],
                "lyrics": "(cached)",
            }

    # Also check for legacy cache files
    legacy_path = os.path.join(output_dir, f"cache_{hash_key}.mp3")
    if os.path.exists(legacy_path):
        return {
            "audio_path": legacy_path,
            "title": f"{song} Remix",
            "genre": style,
            "lyrics": "(cached)",
        }

    return None


def _save_to_cache(artist: str, song: str, style: str, title: str, genre: str, filename: str, output_dir: str):
    """Save song metadata to cache index."""
    hash_key = _get_cache_hash(artist, song, style)
    index = _load_cache_index(output_dir)
    index[hash_key] = {
        "title": title,
        "genre": genre,
        "filename": filename,
    }
    _save_cache_index(output_dir, index)


def generate_lyrics_fast(artist: str, song: str, style: str | None) -> tuple[str, str, str]:
    """Generate lyrics quickly with Claude. Returns (title, lyrics, genre)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found")

    client = anthropic.Anthropic(api_key=api_key)

    # Build style instruction - infer from artist if not specified
    if style:
        style_instruction = f"Style: {style}."
    else:
        style_instruction = f"Match the typical musical style and genre of {artist}."

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Write short song lyrics (under 400 chars) inspired by "{song}" by {artist}. {style_instruction}

Format:
TITLE: [catchy title]
GENRE: [one-word genre, e.g., rock, pop, hip-hop, R&B, country, grunge, metal, jazz, etc.]

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
    genre = None
    lyrics_start = 0

    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("GENRE:"):
            genre = line.replace("GENRE:", "").strip().lower()
        elif line.strip().startswith("["):
            lyrics_start = i
            break

    # Fallback if genre wasn't parsed
    if not genre:
        genre = style or f"{artist} style"

    lyrics = '\n'.join(lines[lyrics_start:]).strip()

    # Ensure under 400 chars for MiniMax
    if len(lyrics) > 400:
        lyrics = lyrics[:400].rsplit('\n', 1)[0]

    return title, lyrics, genre


def generate_song_suno(
    artist: str,
    album: str,
    style: str | None = None,
    output_dir: str = "output"
) -> dict:
    """
    Generate a complete song: Claude (lyrics) + MiniMax (music+vocals).

    2 API calls total. Skips Genius entirely.

    Args:
        artist: Artist name for inspiration
        album: Song/album name for inspiration
        style: Optional genre/style override. If None, infers from artist.
        output_dir: Directory for output files

    Returns:
        dict with 'audio_path', 'title', 'lyrics'
    """
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise ValueError("REPLICATE_API_TOKEN not found")

    os.makedirs(output_dir, exist_ok=True)

    # Use style or "artist-style" for cache key
    cache_style = style or f"{artist}-style"

    # Check cache first (includes both new index and legacy files)
    cached = _get_cached_song(artist, album, cache_style, output_dir)
    if cached:
        print(f"  Using cached song: {os.path.basename(cached['audio_path'])}")
        return cached

    # Step 1: Generate lyrics with Claude (~3 sec)
    print(f"  Generating lyrics with Claude...")
    title, lyrics, genre = generate_lyrics_fast(artist, album, style)
    print(f"  Generated: {title} ({genre})")

    # Generate readable filename
    hash_key = _get_cache_hash(artist, album, cache_style)
    safe_title = _sanitize_filename(title)
    filename = f"{safe_title}_{hash_key}.mp3"
    audio_path = os.path.join(output_dir, filename)

    # Step 2: Generate music with MiniMax music-1.5 (better quality, up to 4 min)
    print(f"  Generating music with MiniMax...")

    # Build music prompt using the genre (either provided or inferred)
    prompt = f"{genre}, professional production, catchy melody, inspired by {artist}"

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

    # Save with readable filename
    with open(audio_path, "wb") as f:
        f.write(audio_content)

    # Save to cache index for future lookups
    _save_to_cache(artist, album, cache_style, title, genre, filename, output_dir)

    print(f"  Complete! Saved to {filename}")

    return {
        "audio_path": audio_path,
        "title": title,
        "lyrics": lyrics,
        "genre": genre,
    }
