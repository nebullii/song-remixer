"""Suno AI integration for generating songs with actual singing vocals."""

import os
import time
import requests

BASE_URL = "https://studio-api.suno.ai"
CLERK_URL = "https://clerk.suno.ai"


def get_session():
    """Get session token from environment."""
    cookie = os.getenv("SUNO_COOKIE")
    if not cookie:
        raise ValueError(
            "SUNO_COOKIE not found. To get it:\n"
            "1. Go to suno.ai and log in\n"
            "2. Open browser DevTools (F12) → Application → Cookies\n"
            "3. Copy the entire cookie string (or just __client value)\n"
            "4. Set SUNO_COOKIE in your .env file"
        )
    return cookie


def get_auth_token(session_cookie: str) -> str:
    """Exchange session cookie for auth token."""
    headers = {
        "Cookie": session_cookie,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    response = requests.get(
        f"{CLERK_URL}/v1/client?_clerk_js_version=4.73.4",
        headers=headers
    )
    response.raise_for_status()

    data = response.json()
    sessions = data.get("response", {}).get("sessions", [])
    if not sessions:
        raise ValueError("No active Suno session found. Please log in again.")

    return sessions[0].get("last_active_token", {}).get("jwt")


def generate_song(lyrics: str, title: str, style: str = "pop", wait: bool = True) -> dict:
    """
    Generate a song using Suno AI.

    Args:
        lyrics: The song lyrics
        title: Song title
        style: Music style/genre description
        wait: Whether to wait for completion

    Returns:
        dict with song URLs and metadata
    """
    session_cookie = get_session()
    token = get_auth_token(session_cookie)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    # Create song generation request
    payload = {
        "prompt": lyrics,
        "tags": style,
        "title": title,
        "make_instrumental": False,
        "mv": "chirp-v3-5",  # Latest model
        "wait_audio": False
    }

    print(f"  Sending to Suno AI...")
    response = requests.post(
        f"{BASE_URL}/api/generate/v2/",
        headers=headers,
        json=payload
    )
    response.raise_for_status()

    songs = response.json()
    if not songs:
        raise ValueError("Suno returned empty response")

    song_ids = [s["id"] for s in songs]
    print(f"  Song generation started (IDs: {song_ids})")

    if not wait:
        return songs

    # Poll for completion
    return wait_for_songs(song_ids, headers)


def wait_for_songs(song_ids: list, headers: dict, timeout: int = 300) -> list:
    """Wait for songs to finish generating."""
    print(f"  Waiting for Suno to generate song...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(
            f"{BASE_URL}/api/feed/?ids={','.join(song_ids)}",
            headers=headers
        )
        response.raise_for_status()

        songs = response.json()

        # Check if all songs are complete
        all_complete = all(
            s.get("status") == "complete"
            for s in songs
        )

        if all_complete:
            print(f"  Song generation complete!")
            return songs

        # Check for errors
        for s in songs:
            if s.get("status") == "error":
                raise ValueError(f"Suno generation failed: {s.get('error_message', 'Unknown error')}")

        # Show progress
        for s in songs:
            status = s.get("status", "unknown")
            progress = s.get("progress", 0)
            if status == "processing":
                print(f"  Processing: {progress}%", end="\r")

        time.sleep(5)

    raise TimeoutError("Suno generation timed out")


def download_song(audio_url: str, output_path: str) -> str:
    """Download the generated song."""
    print(f"  Downloading song...")

    response = requests.get(audio_url)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


def generate_and_download(
    lyrics: str,
    title: str,
    style: str = "pop",
    output_dir: str = "output"
) -> str:
    """
    Generate a song with Suno and download it.

    This is the main function to call - handles everything.
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    # Generate song
    songs = generate_song(lyrics, title, style, wait=True)

    if not songs:
        raise ValueError("No songs generated")

    # Get the first song (Suno generates 2 variations)
    song = songs[0]
    audio_url = song.get("audio_url")

    if not audio_url:
        raise ValueError("No audio URL in response")

    # Create safe filename
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in title)[:50]
    safe_title = safe_title.replace(" ", "_")
    output_path = os.path.join(output_dir, f"{safe_title}.mp3")

    # Download
    download_song(audio_url, output_path)

    print(f"  Complete! Saved to {output_path}")
    return output_path
