"""Song Remixer Web App - Single page chat interface."""

import os
import re
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv

from src.lyrics_fetcher import fetch_song_lyrics
from src.remixer import generate_remixed_song
from src.tts import generate_song_audio  # Fast TTS (no Replicate)
from src.music_generator import generate_and_download as music_generate  # Full generation

load_dotenv()

app = Flask(__name__)

# Serve audio files from output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


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

        # Step 1: Fetch lyrics (single song)
        print(f"Fetching lyrics for '{song_name} by {artist}'...")
        song_data = fetch_song_lyrics(artist, song_name)

        # Step 2: Generate new lyrics with Claude
        print(f"Generating new song with Claude...")
        song = generate_remixed_song(song_data, style_hint=style)

        # Step 3: Generate audio
        # FAST_MODE=true (default) = Edge TTS only (~5 seconds, sounds like reading)
        # FAST_MODE=false = Full Bark+MusicGen (~5+ minutes, has music)
        fast_mode = os.getenv("FAST_MODE", "true").lower() == "true"

        if fast_mode:
            print(f"Generating audio with Edge TTS (fast mode ~5 sec)...")
            audio_path = generate_song_audio(song, output_dir=OUTPUT_DIR)
        else:
            print(f"Generating with Bark + MusicGen (slow ~5 min)...")
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
        audio_filename = os.path.basename(audio_path)

        return jsonify({
            "success": True,
            "title": song["title"],
            "mood": song["mood"],
            "audio_url": f"/audio/{audio_filename}",
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
