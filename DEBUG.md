# Debugging Playbook

## Common Issues & Fixes

### 1. Genius API Issues

**"Album not found"**
- Check exact album name spelling
- Try artist name variations (e.g., "The Beatles" vs "Beatles")
- Some albums have different names on Genius

**"GENIUS_ACCESS_TOKEN not found"**
```bash
# Check if set
echo $GENIUS_ACCESS_TOKEN

# Set it
export GENIUS_ACCESS_TOKEN="your_token_here"
# Or add to .env file
```

**Rate limiting**
- Genius has rate limits; add delays between requests if needed
- Check response status codes

---

### 2. Anthropic API Issues

**"ANTHROPIC_API_KEY not found"**
```bash
export ANTHROPIC_API_KEY="your_key_here"
```

**Response parsing fails**
- Check the raw response in debug mode
- AI might not follow exact format; make parser more flexible

**Empty or weird lyrics**
- Adjust the prompt
- Check if themes/vocabulary extraction worked

---

### 3. TTS Issues

**"edge-tts" errors**
```bash
# Reinstall
pip install --upgrade edge-tts

# Test directly
edge-tts --text "Hello world" --write-media test.mp3
```

**Audio sounds robotic**
- Try different voices (see `list_available_voices()`)
- Adjust rate/pitch in MOOD_RATE config

**File not created**
- Check output directory exists
- Check write permissions

---

### 4. Quick Debug Commands

```bash
# Test Genius connection
python -c "
from dotenv import load_dotenv
load_dotenv()
from src.lyrics_fetcher import get_genius_client
client = get_genius_client()
print('Genius OK')
"

# Test Anthropic connection
python -c "
from dotenv import load_dotenv
load_dotenv()
from src.remixer import get_client
client = get_client()
print('Anthropic OK')
"

# Test TTS
python -c "
from src.tts import generate_song_audio
song = {'title': 'Test', 'mood': 'dreamy', 'lyrics': 'Hello world, this is a test.'}
path = generate_song_audio(song)
print(f'Created: {path}')
"
```

---

### 5. Environment Setup Checklist

```bash
# 1. Create virtual env
python -m venv venv
source venv/bin/activate

# 2. Install deps
pip install -r requirements.txt

# 3. Copy and fill env
cp .env.example .env
# Edit .env with your API keys

# 4. Test imports
python -c "import lyricsgenius, anthropic, edge_tts; print('All imports OK')"
```

---

## Debug Mode Flag

Add `--debug` flag to main.py for verbose output:
- Print raw API responses
- Show intermediate data (themes, vocabulary)
- Save debug logs to `output/debug.log`
