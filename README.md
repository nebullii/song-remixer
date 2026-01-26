# Song Remixer

Song Remixer is a Flask web app that turns a user's “Song by Artist” prompt into a fresh, stylized remix. It fetches lyrics, analyzes themes and mood, rewrites the lyrics, and generates a new audio track using AI music and vocal synthesis. The app supports optional style hints and vocal gender cues, then serves the resulting audio file.

## Features
- Single-page web UI for quick remix requests
- Lyrics fetching and theme extraction
- AI-generated remix lyrics and audio output
- Optional style hints and vocal gender inference
- Dockerized deployment to Google Cloud Run

## Project Structure
- `app.py`: Flask web app and API endpoints
- `src/`: Core remix, lyrics, and audio generation logic
- `templates/`: Web UI
- `deploy.sh`: Cloud Run deployment script
- `cloudbuild.yaml`: Cloud Build configuration

## Requirements
- Python 3.10+
- FFmpeg (installed via system package manager)

## Local Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file for local development:
```
REPLICATE_API_TOKEN=...
ANTHROPIC_API_KEY=...
GENIUS_ACCESS_TOKEN=...
```

Run locally:
```bash
python app.py
```
Then open `http://localhost:5050`.

## Usage
Use the format:
```
Song by Artist
```
Optionally add style and vocal hints:
```
Song by Artist (rock, energetic, female)
```

## Deployment (Cloud Run)
Deploy with:
```bash
GCLOUD_PROJECT_ID=your-project-id GCLOUD_REGION=us-central1 ./deploy.sh
```

Secrets are read from Secret Manager in production. Create these secrets:
- `replicate-api-token`
- `anthropic-api-key`
- `genius-access-token`

## Notes
- Genius does not provide full lyrics via API, so lyrics are scraped from the song page.
- Some songs may fail if the lyrics page blocks scraping.
