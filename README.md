# Song Remixer

AI-powered song generator that creates original songs with vocals and instrumentals, inspired by your favorite artists.

## Features

- **AI Lyrics Generation** - Creates original lyrics inspired by any artist's style
- **Full Song Output** - Generates complete songs with vocals and instrumentals
- **Multiple Audio Modes** - Choose between speed and quality
- **Smart Caching** - Instant playback for repeated requests
- **Web Interface** - Simple browser-based UI

## How It Works

```
User Input → Claude AI → MiniMax Music → Complete Song
     ↓           ↓             ↓
"Song by     Generates     Full song with
 Artist"     lyrics        vocals + music
```

## Audio Modes

| Mode | Speed | Quality | APIs Used |
|------|-------|---------|-----------|
| `suno` (default) | ~30-60s | High | Claude + MiniMax |
| `quick` | ~1 min | Medium | Genius + Claude + MusicGen |
| `fast` | ~5s | Low | Genius + Claude + Edge TTS |
| `full` | ~5 min | Highest | Genius + Claude + Bark + MusicGen |

## Quick Start

### Prerequisites

- Python 3.10+
- ffmpeg (for audio processing)
  ```bash
  # macOS
  brew install ffmpeg

  # Ubuntu
  sudo apt-get install ffmpeg
  ```

### Installation

```bash
git clone https://github.com/nebullii/song-remixer.git
cd song-remixer
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
ANTHROPIC_API_KEY=your_anthropic_key
REPLICATE_API_TOKEN=your_replicate_token
AUDIO_MODE=suno
```

Get your API keys:
- [Anthropic Console](https://console.anthropic.com/) - For Claude AI
- [Replicate](https://replicate.com/account/api-tokens) - For MiniMax Music

### Run

```bash
python app.py
```

Open [http://localhost:5050](http://localhost:5050)

## Usage

Enter a song and artist in any of these formats:

```
Billie Jean by Michael Jackson
Thriller - Michael Jackson
Michael Jackson: Beat It
```

Add style hints in parentheses:

```
Billie Jean by Michael Jackson (80s synth, energetic)
Hello by Adele (acoustic, melancholic, female)
```

## Project Structure

```
song-remixer/
├── app.py                 # Flask web app
├── deploy.sh              # Google Cloud Run deployment
├── src/
│   ├── suno_generator.py  # Claude + MiniMax pipeline
│   ├── music_generator.py # MusicGen + Bark pipeline
│   ├── lyrics_fetcher.py  # Genius API integration
│   ├── remixer.py         # Claude lyrics generation
│   └── tts.py             # Edge TTS vocals
└── output/                # Generated audio files
```

## Deployment

Deploy to Google Cloud Run:

```bash
./deploy.sh
```

Requires secrets in Google Secret Manager:
- `replicate-api-token`
- `anthropic-api-key`

## License

MIT
