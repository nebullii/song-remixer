"""Song Remixer Web App - Single page chat interface."""

import os
import re
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from dotenv import load_dotenv

try:
    from google.cloud import storage
except Exception:
    storage = None

from src.lyrics_fetcher import fetch_song_lyrics
from src.remixer import generate_remixed_song
from src.quick_generator import generate_quick_song  # TTS + single instrumental (~1 min)
from src.tts import generate_song_audio  # TTS only, no music (~5 sec)
from src.music_generator import generate_and_download as music_generate  # Full Bark+MusicGen (~5 min)
from src.suno_generator import generate_song_suno  # Suno: single API for everything (~30-60 sec)

load_dotenv()

app = Flask(__name__)

# Security: CORS - only allow same-origin requests
CORS(app, resources={r"/api/*": {"origins": os.getenv("ALLOWED_ORIGINS", "*").split(",")}})

# Security: Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


@app.errorhandler(429)
def ratelimit_handler(e):
    """Return JSON for rate limit errors."""
    return jsonify({"error": e.description or "Rate limit exceeded. Please try again later."}), 429

# Serve audio files from output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
GCS_BUCKET = os.getenv("GCS_BUCKET", "sound-remixer")
SONGS_DB = os.path.join(OUTPUT_DIR, "songs.json")


def load_songs_db() -> list:
    """Load songs metadata from JSON file."""
    if not os.path.exists(SONGS_DB):
        return []
    try:
        with open(SONGS_DB, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_song_to_db(song: dict):
    """Save a song's metadata to the JSON database."""
    songs = load_songs_db()
    song["created_at"] = datetime.now().isoformat()
    songs.insert(0, song)  # Add to beginning (newest first)
    # Keep only last 100 songs
    songs = songs[:100]
    try:
        with open(SONGS_DB, "w") as f:
            json.dump(songs, f, indent=2)
    except Exception as e:
        print(f"Failed to save song to DB: {e}")


def get_cache_key(artist: str, song: str, style: str) -> str:
    """Generate consistent cache key."""
    import hashlib
    key = f"{artist}_{song}_{style}".lower()
    return hashlib.md5(key.encode()).hexdigest()[:8]


def sanitize_filename(name: str) -> str:
    """Convert a title to a safe filename."""
    safe = re.sub(r'[^\w\s-]', '', name)
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe[:50]


def get_readable_filename(title: str, cache_key: str) -> str:
    """Generate a readable filename with hash suffix."""
    safe_title = sanitize_filename(title)
    return f"{safe_title}_{cache_key}.mp3"


def check_gcs_cache(bucket_name: str, cache_key: str) -> dict | None:
    """Check if song exists in GCS cache. Returns metadata + URL if found."""
    if not bucket_name or storage is None:
        return None
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"cache_{cache_key}.mp3")
        if blob.exists():
            blob.reload()
            metadata = blob.metadata or {}
            return {
                "audio_url": f"https://storage.googleapis.com/{bucket_name}/cache_{cache_key}.mp3",
                "title": metadata.get("title", "Cached Song"),
                "style": metadata.get("style"),
                "cached": True
            }
    except Exception as e:
        print(f"GCS cache check failed: {e}")
    return None


def upload_to_gcs(file_path: str, bucket_name: str, metadata: dict = None, blob_name: str = None) -> str | None:
    if not bucket_name or storage is None:
        return None
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob_name = blob_name or os.path.basename(file_path)
        blob = bucket.blob(blob_name)
        blob.cache_control = "public, max-age=604800"
        if metadata:
            blob.metadata = metadata
        blob.upload_from_filename(file_path, content_type="audio/mpeg")
        return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    except Exception as e:
        print(f"GCS upload failed: {e}")
        return None


def list_songs_from_gcs(bucket_name: str, limit: int = 20) -> list:
    """List recent songs from GCS bucket with metadata."""
    if not bucket_name or storage is None:
        return list_local_songs(limit)
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blobs = list(bucket.list_blobs())

        # Sort by creation time (newest first)
        blobs.sort(key=lambda b: b.time_created or "", reverse=True)

        songs = []
        for blob in blobs[:limit]:
            if not blob.name.endswith('.mp3'):
                continue
            # Reload to get metadata
            blob.reload()
            metadata = blob.metadata or {}
            songs.append({
                "title": metadata.get("title", blob.name.replace(".mp3", "").replace("_", " ").title()),
                "artist": metadata.get("artist", ""),
                "style": metadata.get("style", ""),
                "source_song": metadata.get("source_song", ""),
                "audio_url": f"https://storage.googleapis.com/{bucket_name}/{blob.name}",
                "created_at": blob.time_created.isoformat() if blob.time_created else None
            })
        return songs if songs else list_local_songs(limit)
    except Exception as e:
        print(f"GCS list failed: {e}")
        return list_local_songs(limit)


def list_local_songs(limit: int = 20) -> list:
    """Fallback: list songs from local output directory."""
    import glob
    from datetime import datetime

    songs = []
    mp3_files = glob.glob(os.path.join(OUTPUT_DIR, "*.mp3"))

    # Sort by modification time (newest first)
    mp3_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    for filepath in mp3_files[:limit]:
        filename = os.path.basename(filepath)
        title = filename.replace(".mp3", "").replace("_", " ").title()
        songs.append({
            "title": title,
            "artist": "",
            "style": "",
            "source_song": "",
            "audio_url": f"/audio/{filename}",
            "created_at": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
        })
    return songs


def parse_user_input(user_input: str) -> tuple[str, str, str, str | None]:
    """Parse user input to extract song name, artist, optional style, and optional vocal gender."""
    # Sanitize input - remove quotes and extra whitespace
    user_input = user_input.strip()
    user_input = user_input.replace('"', '').replace("'", '').replace('"', '').replace('"', '')
    user_input = re.sub(r'\s+', ' ', user_input)  # Normalize whitespace
    
    style = None  # None = infer from artist's typical style
    vocal_gender = None

    # Check for style hints in parentheses at the end
    if "(" in user_input and user_input.endswith(")"):
        style_start = user_input.rfind("(")
        raw_hint = user_input[style_start + 1:-1].strip()
        user_input = user_input[:style_start].strip()
        if raw_hint:
            lowered = raw_hint.lower()
            if re.search(r"\b(female|woman|girl)\b", lowered):
                vocal_gender = "female"
            elif re.search(r"\b(male|man|boy)\b", lowered):
                vocal_gender = "male"
            elif re.search(r"\b(neutral|androgynous)\b", lowered):
                vocal_gender = "neutral"

            # Remove any gender tokens from the style hint
            cleaned = re.sub(r"\b(female|woman|girl|male|man|boy|neutral|androgynous)\b", "", raw_hint, flags=re.IGNORECASE)
            cleaned = re.sub(r"[,\s]+", " ", cleaned).strip(" ,")
            if cleaned:
                style = cleaned

    # Try different separators
    if " by " in user_input.lower():
        idx = user_input.lower().index(" by ")
        song_name = user_input[:idx].strip()
        artist = user_input[idx + 4:].strip()
    elif " - " in user_input:
        parts = user_input.split(" - ", 1)
        song_name = parts[0].strip()
        artist = parts[1].strip()
    elif ": " in user_input:
        parts = user_input.split(": ", 1)
        artist = parts[0].strip()
        song_name = parts[1].strip()
    else:
        raise ValueError(
            "Please use format: 'Song by Artist' or 'Song - Artist'"
        )

    return song_name, artist, style, vocal_gender


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/songs")
def list_songs():
    """List recent community songs - from GCS in prod, local DB for dev."""
    # Try GCS first (production)
    songs = list_songs_from_gcs(GCS_BUCKET)
    # Fallback to local DB (development)
    if not songs:
        songs = load_songs_db()
    return jsonify({"songs": songs})


@app.route("/explore")
def explore():
    """Gallery page showing all generated songs."""
    return render_template("explore.html")


@app.route("/api/remix", methods=["POST"])
@limiter.limit("5 per hour", error_message="Rate limit exceeded. You can create up to 5 songs per hour.")
@limiter.limit("20 per day", error_message="Daily limit exceeded. You can create up to 20 songs per day.")
def remix():
    data = request.json
    user_input = data.get("message", "")

    if not user_input:
        return jsonify({"error": "Please enter a song name"}), 400

    try:
        # Parse input
        song_name, artist, style, vocal_gender = parse_user_input(user_input)

        # AUDIO_MODE: "suno" (fastest), "quick", "fast", or "full"
        #   suno  = Single Suno API call, skips Genius+Claude (~30-60 sec)
        #   quick = Edge TTS + single MusicGen instrumental (~1 min)
        #   fast  = Edge TTS only, no music (~5 sec)
        #   full  = Bark + MusicGen per section (~5+ min)
        audio_mode = os.getenv("AUDIO_MODE", "suno").lower()

        # Suno mode: single API, no Genius/Claude needed
        if audio_mode == "suno":
            # Check GCS cache first (saves API costs in production)
            cache_key = get_cache_key(artist, song_name, style or f"{artist}-style")
            cached = check_gcs_cache(GCS_BUCKET, cache_key)
            if cached:
                print(f"Using GCS cached song!")
                # For cached, use style from GCS metadata or fallback
                cached_style = cached.get("style") or style or f"{artist} style"
                return jsonify({
                    "success": True,
                    "title": cached["title"],
                    "mood": "generated",
                    "audio_url": cached["audio_url"],
                    "source_song": song_name,
                    "themes": [cached_style]
                })

            print(f"Generating complete song with Suno (~30-60 sec)...")
            result = generate_song_suno(
                artist=artist,
                album=song_name,
                style=style,
                output_dir=OUTPUT_DIR,
            )
            audio_filename = os.path.basename(result["audio_path"])

            # Display style: use genre from AI, fallback to style or artist name
            display_style = result.get("genre") or style or f"{artist} style"

            metadata = {
                "title": result["title"],
                "artist": artist,
                "style": display_style,
                "source_song": song_name
            }
            # Use hash-based name for GCS cache lookup, readable name stored in metadata
            gcs_cache_name = f"cache_{cache_key}.mp3"
            gcs_url = upload_to_gcs(result["audio_path"], GCS_BUCKET, metadata, blob_name=gcs_cache_name)
            # Local URL uses the readable filename from suno_generator
            audio_url = gcs_url or f"/audio/{audio_filename}"

            # Save to local DB
            save_song_to_db({
                "title": result["title"],
                "artist": artist,
                "style": display_style,
                "source_song": song_name,
                "audio_url": audio_url
            })

            return jsonify({
                "success": True,
                "title": result["title"],
                "mood": "generated",
                "audio_url": audio_url,
                "source_song": song_name,
                "themes": [display_style]
            })

        # Other modes require Genius + Claude first
        # Step 1: Fetch lyrics (single song)
        print(f"Fetching lyrics for '{song_name} by {artist}'...")
        song_data = fetch_song_lyrics(artist, song_name)

        # Step 2: Generate new lyrics with Claude
        print(f"Generating new song with Claude...")
        song = generate_remixed_song(song_data, style_hint=style)

        # Step 3: Generate audio
        if audio_mode == "fast":
            print(f"Generating with Edge TTS only (no music, ~5 sec)...")
            audio_path = generate_song_audio(song, output_dir=OUTPUT_DIR)
        elif audio_mode == "full":
            print(f"Generating with Bark + MusicGen (slow, ~5 min)...")
            audio_path = music_generate(
                lyrics=song["lyrics"],
                title=song["title"],
                style=style,
                mood=song["mood"],
                vocal_gender=vocal_gender,
                output_dir=OUTPUT_DIR,
                add_harmonies=False,
                add_intro_outro=False,
            )
        else:  # quick
            print(f"Generating with Edge TTS + MusicGen (~1 min)...")
            audio_path = generate_quick_song(
                lyrics=song["lyrics"],
                title=song["title"],
                style=style,
                mood=song["mood"],
                output_dir=OUTPUT_DIR,
            )
        audio_filename = os.path.basename(audio_path)
        source = song_data["tracks"][0]["title"] if song_data["tracks"] else song_name

        # Display style: use explicit style or show artist-inspired
        display_style = style if style else f"{artist} style"

        metadata = {
            "title": song["title"],
            "artist": artist,
            "style": display_style,
            "source_song": source
        }
        gcs_url = upload_to_gcs(audio_path, GCS_BUCKET, metadata)
        audio_url = gcs_url or f"/audio/{audio_filename}"

        # Save to local DB
        save_song_to_db({
            "title": song["title"],
            "artist": artist,
            "style": display_style,
            "source_song": source,
            "audio_url": audio_url
        })

        return jsonify({
            "success": True,
            "title": song["title"],
            "mood": song["mood"],
            "audio_url": audio_url,
            "source_song": source,
            "themes": song_data["themes"][:10]
        })

    except ValueError as e:
        print(f"ValueError: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    # Avoid macOS AirTunes/AirPlay receiver on port 5000.
    app.run(debug=True, port=5050)
