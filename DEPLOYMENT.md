# Google Cloud Deployment Guide

## Quick Start

### Prerequisites

1. **Install Google Cloud SDK**
   ```bash
   # macOS
   brew install --cask google-cloud-sdk
   
   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate**
   ```bash
   gcloud auth login
   ```

3. **Set your API keys** (in your local `.env` file):
   ```
   REPLICATE_API_TOKEN=your_token
   ANTHROPIC_API_KEY=your_key
   GENIUS_ACCESS_TOKEN=your_token
   ```

### Deploy to Google Cloud Run

**One-command deployment:**

```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
- ✅ Build a Docker container
- ✅ Push to Google Container Registry
- ✅ Deploy to Cloud Run
- ✅ Configure environment variables
- ✅ Set up free tier limits

**Your app will be live in ~5 minutes!**

---

## Manual Deployment

If you prefer manual steps:

### 1. Create a Google Cloud Project

```bash
gcloud projects create song-remixer --name="Song Remixer"
gcloud config set project song-remixer
```

### 2. Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 3. Build and Deploy

```bash
# Build container
gcloud builds submit --tag gcr.io/song-remixer/song-remixer

# Deploy to Cloud Run
gcloud run deploy song-remixer \
    --image gcr.io/song-remixer/song-remixer \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 600 \
    --set-env-vars "FAST_MODE=true"
```

### 4. Set Environment Variables

Go to Cloud Console and add your API keys:
https://console.cloud.google.com/run

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `REPLICATE_API_TOKEN` | Yes | For music generation |
| `ANTHROPIC_API_KEY` | Yes | For lyrics generation |
| `GENIUS_ACCESS_TOKEN` | Yes | For fetching lyrics |
| `FAST_MODE` | No | Set to `false` for full quality (default: `true`) |

### Performance Modes

**Fast Mode (default for web app):**
- ⏱️ Generation time: ~1-2 minutes
- ❌ No intro/outro
- ❌ No vocal harmonies
- ✅ Section-specific effects
- ✅ Dynamic mixing

**Full Quality Mode:**
```bash
# Set FAST_MODE=false in Cloud Run
```
- ⏱️ Generation time: ~3-5 minutes
- ✅ Intro/outro
- ✅ Vocal harmonies
- ✅ All enhancements

---

## Cost Estimate

### Google Cloud Run - Free Tier

**Included free every month:**
- 2 million requests
- 360,000 GB-seconds of memory
- 180,000 vCPU-seconds

**Our configuration:**
- Memory: 2 GB
- CPU: 1 vCPU
- Timeout: 10 minutes

**Estimated costs:**
- First ~500 songs/month: **FREE**
- After that: ~$0.10 per song

### API Costs

**Replicate (MusicGen + Bark):**
- ~$0.05 per song section
- ~$0.30 per complete song

**Anthropic (Claude):**
- ~$0.01 per lyrics generation

**Total per song: ~$0.31**

---

## Monitoring

### View Logs

```bash
gcloud run logs tail song-remixer --region us-central1
```

### View Metrics

```bash
# Open in browser
gcloud run services describe song-remixer --region us-central1
```

Or visit: https://console.cloud.google.com/run

---

## Updating Your Deployment

After making code changes:

```bash
./deploy.sh
```

That's it! The script handles everything.

---

## Local Testing with Docker

Test the Docker container locally before deploying:

```bash
# Build
docker build -t song-remixer .

# Run
docker run -p 8080:8080 \
    -e REPLICATE_API_TOKEN=$REPLICATE_API_TOKEN \
    -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    -e GENIUS_ACCESS_TOKEN=$GENIUS_ACCESS_TOKEN \
    song-remixer

# Visit http://localhost:8080
```

---

## Troubleshooting

### Build fails

```bash
# Check Docker is running
docker ps

# Try building locally first
docker build -t song-remixer .
```

### Deployment fails

```bash
# Check you're authenticated
gcloud auth list

# Check project is set
gcloud config get-value project
```

### App crashes

```bash
# Check logs
gcloud run logs tail song-remixer --region us-central1

# Common issues:
# - Missing API keys
# - Insufficient memory (increase to 4Gi)
# - Timeout (increase to 900s)
```

### Out of memory

```bash
# Increase memory to 4Gi
gcloud run services update song-remixer \
    --memory 4Gi \
    --region us-central1
```

---

## Custom Domain

To use your own domain:

1. **Verify domain ownership** in Cloud Console
2. **Map domain to service:**
   ```bash
   gcloud run domain-mappings create \
       --service song-remixer \
       --domain yourdomain.com \
       --region us-central1
   ```
3. **Update DNS** with provided records

---

## Security

### API Keys

**Never commit API keys to git!**

Set them via Cloud Console:
1. Go to Cloud Run service
2. Click "Edit & Deploy New Revision"
3. Add environment variables
4. Deploy

### Authentication

To require authentication:

```bash
gcloud run services update song-remixer \
    --no-allow-unauthenticated \
    --region us-central1
```

---

## Support

- **Cloud Run docs**: https://cloud.google.com/run/docs
- **Pricing calculator**: https://cloud.google.com/products/calculator
- **Free tier limits**: https://cloud.google.com/free

---

## Summary

✅ **Free tier eligible** - First 500 songs/month free  
✅ **Auto-scaling** - Handles traffic spikes  
✅ **Fast deployment** - Live in 5 minutes  
✅ **Easy updates** - One command to redeploy  
✅ **Global CDN** - Fast worldwide access  

**Total setup time: ~10 minutes**
