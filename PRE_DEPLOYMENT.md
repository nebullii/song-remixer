# Pre-Deployment Checklist

Complete these steps before deploying to Google Cloud Run.

## ✅ Step 1: Install Google Cloud SDK

**macOS:**
```bash
brew install --cask google-cloud-sdk
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Windows:**
Download from: https://cloud.google.com/sdk/docs/install

**Verify installation:**
```bash
gcloud --version
```

---

## ✅ Step 2: Authenticate with Google Cloud

```bash
# Login to your Google account
gcloud auth login

# Set up application default credentials
gcloud auth application-default login
```

This will open a browser window for authentication.

---

## ✅ Step 3: Create/Select Google Cloud Project

**Option A: Create new project**
```bash
# Create project (choose a unique ID)
gcloud projects create song-remixer-123 --name="Song Remixer"

# Set as active project
gcloud config set project song-remixer-123
```

**Option B: Use existing project**
```bash
# List your projects
gcloud projects list

# Set active project
gcloud config set project YOUR_PROJECT_ID
```

---

## ✅ Step 4: Enable Billing

1. Go to: https://console.cloud.google.com/billing
2. Link a billing account to your project
3. **Don't worry**: Free tier covers ~500 songs/month!

**Verify billing is enabled:**
```bash
gcloud beta billing projects describe $(gcloud config get-value project)
```

---

## ✅ Step 5: Verify API Keys

Check your `.env` file has all required keys:

```bash
cat .env
```

**Required variables:**
```
REPLICATE_API_TOKEN=r8_...
ANTHROPIC_API_KEY=sk-ant-...
GENIUS_ACCESS_TOKEN=...
```

**Get missing keys:**
- **Replicate**: https://replicate.com/account/api-tokens
- **Anthropic**: https://console.anthropic.com/
- **Genius**: https://genius.com/api-clients

---

## ✅ Step 6: Test Locally

**Test the Flask app:**
```bash
python app.py
```

Visit http://localhost:5050 and try generating a song.

**Test with Docker (optional but recommended):**
```bash
# Build
docker build -t song-remixer .

# Run
docker run -p 8080:8080 \
    -e REPLICATE_API_TOKEN=$REPLICATE_API_TOKEN \
    -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    -e GENIUS_ACCESS_TOKEN=$GENIUS_ACCESS_TOKEN \
    -e FAST_MODE=true \
    song-remixer

# Test at http://localhost:8080
```

---

## ✅ Step 7: Review Deployment Configuration

**Check deploy.sh settings:**
```bash
cat deploy.sh | grep -E "PROJECT_ID|REGION|SERVICE_NAME"
```

**Default values:**
- Project ID: `song-remixer` (change if needed)
- Region: `us-central1` (closest to you)
- Service: `song-remixer`

**To customize, edit deploy.sh or set env vars:**
```bash
export GCLOUD_PROJECT_ID="my-custom-project"
export GCLOUD_REGION="us-west1"
```

---

## ✅ Step 8: Estimate Costs

**Free tier (monthly):**
- 2M requests
- 360,000 GB-seconds
- 180,000 vCPU-seconds

**Our usage per song:**
- ~2 GB memory × 120 seconds = 240 GB-seconds
- ~1 vCPU × 120 seconds = 120 vCPU-seconds

**Free tier covers: ~1,500 songs/month**

**After free tier:**
- $0.10 per song (Cloud Run)
- $0.31 per song (API costs)
- **Total: ~$0.41 per song**

---

## ✅ Step 9: Pre-Deployment Checklist

Run this verification script:

```bash
# Check gcloud is installed
command -v gcloud >/dev/null 2>&1 && echo "✅ gcloud installed" || echo "❌ Install gcloud"

# Check authentication
gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1 && echo "✅ Authenticated" || echo "❌ Run: gcloud auth login"

# Check project is set
gcloud config get-value project >/dev/null 2>&1 && echo "✅ Project set: $(gcloud config get-value project)" || echo "❌ Set project"

# Check API keys
[ -n "$REPLICATE_API_TOKEN" ] && echo "✅ REPLICATE_API_TOKEN set" || echo "⚠️  REPLICATE_API_TOKEN not set"
[ -n "$ANTHROPIC_API_KEY" ] && echo "✅ ANTHROPIC_API_KEY set" || echo "⚠️  ANTHROPIC_API_KEY not set"
[ -n "$GENIUS_ACCESS_TOKEN" ] && echo "✅ GENIUS_ACCESS_TOKEN set" || echo "⚠️  GENIUS_ACCESS_TOKEN not set"

# Check Docker (optional)
command -v docker >/dev/null 2>&1 && echo "✅ Docker installed" || echo "⚠️  Docker not installed (optional)"

echo ""
echo "Ready to deploy? Run: ./deploy.sh"
```

---

## ✅ Step 10: Deploy!

When all checks pass:

```bash
./deploy.sh
```

**Deployment takes ~5 minutes.**

You'll get:
- 🌐 Live URL
- 📊 Monitoring dashboard link
- 📝 Instructions for setting API keys (if needed)

---

## Post-Deployment

### Set API Keys in Cloud Run (if not set during deploy)

1. Go to: https://console.cloud.google.com/run
2. Click on `song-remixer` service
3. Click "Edit & Deploy New Revision"
4. Scroll to "Variables & Secrets"
5. Add:
   - `REPLICATE_API_TOKEN`
   - `ANTHROPIC_API_KEY`
   - `GENIUS_ACCESS_TOKEN`
   - `FAST_MODE=true`
6. Click "Deploy"

### Monitor Your App

```bash
# View logs
gcloud run logs tail song-remixer --region us-central1

# View service details
gcloud run services describe song-remixer --region us-central1

# Open in browser
gcloud run services describe song-remixer --region us-central1 --format='value(status.url)' | xargs open
```

### Update After Changes

```bash
# Make code changes, then:
./deploy.sh
```

---

## Troubleshooting

### "gcloud: command not found"
```bash
# Restart terminal after installing gcloud
exec -l $SHELL
```

### "You do not have permission"
```bash
# Re-authenticate
gcloud auth login
gcloud auth application-default login
```

### "Billing not enabled"
1. Go to: https://console.cloud.google.com/billing
2. Link billing account
3. Enable billing for your project

### "API not enabled"
```bash
# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### "Build failed"
```bash
# Test Docker build locally first
docker build -t song-remixer .

# Check for errors in output
```

---

## Quick Start (TL;DR)

```bash
# 1. Install gcloud
brew install --cask google-cloud-sdk

# 2. Authenticate
gcloud auth login

# 3. Create project
gcloud projects create song-remixer-123
gcloud config set project song-remixer-123

# 4. Enable billing (in web console)
open https://console.cloud.google.com/billing

# 5. Set API keys in .env
export REPLICATE_API_TOKEN=your_token
export ANTHROPIC_API_KEY=your_key
export GENIUS_ACCESS_TOKEN=your_token

# 6. Deploy!
./deploy.sh
```

**That's it! Your app will be live in ~5 minutes.**
