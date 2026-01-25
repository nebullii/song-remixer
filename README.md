# Song Remixer

Create an original pop song inspired by an album, then generate a vocal track and an instrumental track, and mix them together.

## What it does
- Fetches lyrics from Genius to extract themes and vocabulary.
- Uses Anthropic to write a new, original song (structured verses/chorus/bridge).
- Generates vocals with Edge TTS.
- Generates instrumentals with Replicate (MusicGen) and mixes them with the vocals.

## Requirements
- Python 3.10+
- ffmpeg (required by pydub for MP3 read/write)
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt-get install ffmpeg`

## Setup
```sh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:
```env
GENIUS_ACCESS_TOKEN=your_genius_token_here
ANTHROPIC_API_KEY=your_anthropic_key_here
REPLICATE_API_TOKEN=your_replicate_token_here
```

Notes:
- `SUNO_COOKIE` appears in `.env.example` but is not used in the codebase.
- `REPLICATE_MUSICGEN_MODEL` is optional; it defaults to the model ID in `src/music_generator.py`.

## Run the web app
```sh
python app.py
```
Open `http://localhost:5050`.

Input format examples:
- `Thriller by Michael Jackson`
- `Rumours - Fleetwood Mac`
- `Adele: 25 (80s synth, dreamy, female)`

The optional parentheses allow a style hint; if you include `male`, `female`, or `neutral`, it will bias the vocal gender.

## Run the CLI
```sh
python -m src.main
```
Follow the prompt and provide input in the same format as above.

## Output
Audio files are written to the `output/` directory.

## Project layout
- `app.py` - Flask web app
- `src/main.py` - CLI
- `src/lyrics_fetcher.py` - Genius API + lyric scraping
- `src/remixer.py` - Anthropic lyric generation
- `src/tts.py` - Edge TTS vocals
- `src/music_generator.py` - Replicate MusicGen + mixing
- `src/voice.py` - Voice selection heuristics

## Known limitations
- Vocals and instrumentals are not tempo- or key-synced. Expect occasional mismatch.
- Genius rate limits apply; fetching many tracks may be slow.
