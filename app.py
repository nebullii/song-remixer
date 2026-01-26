"""Song Remixer Web App - Single page chat interface."""

import os
import re
from flask import Flask, render_template, request, jsonify, send_from_directory
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

# Serve audio files from output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
GCS_BUCKET = os.getenv("GCS_BUCKET", "sound-remixer")


def upload_to_gcs(file_path: str, bucket_name: str) -> str | None:
    if not bucket_name or storage is None:
        return None
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob_name = os.path.basename(file_path)
        blob = bucket.blob(blob_name)
        blob.cache_control = "public, max-age=604800"
        blob.upload_from_filename(file_path, content_type="audio/mpeg")
        return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    except Exception as e:
        print(f"GCS upload failed: {e}")
        return None


def parse_user_input(user_input: str) -> tuple[str, str, str, str | None]:
    """Parse user input to extract song name, artist, optional style, and optional vocal gender."""
    # Sanitize input - remove quotes and extra whitespace
    user_input = user_input.strip()
    user_input = user_input.replace('"', '').replace("'", '').replace('"', '').replace('"', '')
    user_input = re.sub(r'\s+', ' ', user_input)  # Normalize whitespace
    
    style = "pop, catchy"
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


@app.route("/api/remix", methods=["POST"])
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
            print(f"Generating complete song with Suno (~30-60 sec)...")
            result = generate_song_suno(
                artist=artist,
                album=song_name,
                style=style,
                output_dir=OUTPUT_DIR,
            )
            audio_filename = os.path.basename(result["audio_path"])
            gcs_url = upload_to_gcs(result["audio_path"], GCS_BUCKET)
            audio_url = gcs_url or f"/audio/{audio_filename}"

            return jsonify({
                "success": True,
                "title": result["title"],
                "mood": "generated",
                "audio_url": audio_url,
                "source_song": song_name,
                "themes": [style]
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
        gcs_url = upload_to_gcs(audio_path, GCS_BUCKET)
        audio_url = gcs_url or f"/audio/{audio_filename}"

        return jsonify({
            "success": True,
            "title": song["title"],
            "mood": song["mood"],
            "audio_url": audio_url,
            "source_song": song_data["tracks"][0]["title"] if song_data["tracks"] else song_name,
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
