"""Song Remixer Web App - Single page chat interface."""

import os
import re
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv

from src.lyrics_fetcher import fetch_album_lyrics
from src.remixer import generate_remixed_song
from src.music_generator import generate_and_download
from src.voice import guess_vocal_gender

load_dotenv()

app = Flask(__name__)

# Serve audio files from output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def parse_user_input(user_input: str) -> tuple[str, str, str, str | None]:
    """Parse user input to extract album, artist, optional style, and optional vocal gender."""
    user_input = user_input.strip()
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
        album = user_input[:idx].strip()
        artist = user_input[idx + 4:].strip()
    elif " - " in user_input:
        parts = user_input.split(" - ", 1)
        album = parts[0].strip()
        artist = parts[1].strip()
    elif ": " in user_input:
        parts = user_input.split(": ", 1)
        artist = parts[0].strip()
        album = parts[1].strip()
    else:
        raise ValueError(
            "Please use format: 'Album by Artist' or 'Album - Artist'"
        )

    return album, artist, style, vocal_gender


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/remix", methods=["POST"])
def remix():
    data = request.json
    user_input = data.get("message", "")

    if not user_input:
        return jsonify({"error": "Please enter an album name"}), 400

    try:
        # Parse input
        album, artist, style, vocal_gender_hint = parse_user_input(user_input)

        # Fetch lyrics
        album_data = fetch_album_lyrics(artist, album)

        # Generate song
        song = generate_remixed_song(album_data, style_hint=style)

        # Decide vocal gender (heuristic + optional hint)
        vocal_gender = guess_vocal_gender(artist, hint=vocal_gender_hint)

        # Generate vocals + instrumental music (singing on beat)
        audio_path = generate_and_download(
            lyrics=song["lyrics"],
            title=song["title"],
            style=style,
            mood=song["mood"],
            vocal_gender=vocal_gender,
            output_dir=OUTPUT_DIR,
            singing_method="bark"  # Use Bark for actual singing vocals + instrumental
        )
        audio_filename = os.path.basename(audio_path)

        return jsonify({
            "success": True,
            "title": song["title"],
            "mood": song["mood"],
            "audio_url": f"/audio/{audio_filename}",
            "tracks_found": album_data["track_count"],
            "themes": album_data["themes"][:10]
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    # Avoid macOS AirTunes/AirPlay receiver on port 5000.
    app.run(debug=True, port=5050)
