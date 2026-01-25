# Song Remixer - Project Knowledgebase

## Project Goal
Build a one-day sprint tool that:
1. Takes an album name as input
2. Fetches lyrics via Genius API
3. Uses AI to remix/create an original song inspired by the album's vocabulary and themes
4. Generates audio using TTS

**Simple UX**: User provides album name → Gets a brand new song (audio file)

## Core Architecture

```
[User Input: Album Name]
        ↓
[Genius API] → Fetch all lyrics from album
        ↓
[Extract] → Vocabulary, themes, mood
        ↓
[Claude AI] → Generate original song lyrics
        ↓
[TTS Engine] → Generate audio file
        ↓
[Output: MP3 file]
```

## Tech Stack
- **Lyrics**: `lyricsgenius` library + Genius API
- **AI Remix**: Anthropic Claude API
- **TTS**: Edge-TTS (free, fast) - modular to swap later
- **CLI**: Rich for nice terminal output

## Key Files
- `src/lyrics_fetcher.py` - Genius API integration
- `src/remixer.py` - AI song generation
- `src/tts.py` - Text-to-speech
- `src/main.py` - CLI entry point

## API Keys Required
- `GENIUS_ACCESS_TOKEN` - Get at https://genius.com/api-clients
- `ANTHROPIC_API_KEY` - Get at https://console.anthropic.com/

## What We're NOT Building (Scope Control)
- No web UI (CLI only for day 1)
- No music/melody generation (speech TTS only)
- No lyrics database/storage
- No user accounts or history

## Quick Commands
```bash
# Run the tool
python -m src.main "Album Name" "Artist Name"

# Test individual components
python -c "from src.lyrics_fetcher import fetch_album_lyrics; ..."
```

## Current Status
- [x] Project setup
- [x] Lyrics fetcher
- [x] AI remixer
- [x] TTS integration
- [x] CLI main entry point
- [ ] Test end-to-end
