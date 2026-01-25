# GitHub Actions Deployment Setup

This repository uses GitHub Actions to automatically deploy to Google Cloud Run when you push to the `deployment` branch.

## 🚀 How It Works

**Automatic Deployment:**
- Push to `deployment` branch → Automatically deploys to Cloud Run
- Manual trigger available in GitHub Actions UI

## 🔧 Setup Instructions

### 1. Create Google Cloud Service Account

```bash
# Set your project ID
export PROJECT_ID=glassy-keyword-474117-j6

# Create service account
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Deployer" \
    --project=$PROJECT_ID

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

# Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=github-actions@${PROJECT_ID}.iam.gserviceaccount.com

# Display the key (copy this for GitHub Secrets)
cat github-actions-key.json
```

### 2. Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `GCP_SA_KEY` | Contents of `github-actions-key.json` |
| `REPLICATE_API_TOKEN` | Your Replicate API token |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GENIUS_ACCESS_TOKEN` | Your Genius API token |

**To add secrets:**
1. Click "New repository secret"
2. Enter name and value
3. Click "Add secret"

### 3. Push to Deployment Branch

```bash
# Make sure you're on deployment branch
git checkout deployment

# Add all changes
git add .

# Commit
git commit -m "Set up automatic deployment"

# Push to GitHub (triggers deployment)
git push origin deployment
```

## 📋 Workflow Details

**File:** `.github/workflows/deploy.yml`

**Triggers:**
- Push to `deployment` branch
- Manual trigger via GitHub Actions UI

**Steps:**
1. Checkout code
2. Authenticate to Google Cloud
3. Build Docker image
4. Push to Google Container Registry
5. Deploy to Cloud Run
6. Display deployment URL

## 🔄 Deployment Workflow

### Development → Deployment

```bash
# Work on main branch
git checkout main
# ... make changes ...
git add .
git commit -m "Add new feature"
git push origin main

# When ready to deploy
git checkout deployment
git merge main
git push origin deployment  # This triggers deployment!
```

### Quick Deploy

```bash
# One-liner to deploy current main
git checkout deployment && git merge main && git push origin deployment && git checkout main
```

## 📊 Monitor Deployments

**View workflow runs:**
- Go to GitHub → Actions tab
- See deployment status and logs

**View Cloud Run logs:**
```bash
gcloud run logs tail song-remixer --region us-central1
```

## 🛠️ Troubleshooting

### Deployment fails with permission error
- Check service account has correct roles
- Verify `GCP_SA_KEY` secret is set correctly

### API key errors
- Verify all API key secrets are set in GitHub
- Check secret names match exactly

### Build fails
- Check Dockerfile syntax
- Verify all dependencies in requirements.txt

## 🔒 Security Notes

- **Never commit** `github-actions-key.json` to git
- **Never commit** `.env` file to git
- Service account key is stored securely in GitHub Secrets
- API keys are stored as GitHub Secrets, not in code

## 📝 Branch Strategy

- `main` - Development branch
- `deployment` - Production deployment branch

**Workflow:**
1. Develop on `main`
2. Test locally
3. Merge to `deployment` when ready
4. GitHub Actions automatically deploys

---

## Quick Reference

```bash
# Create deployment branch (already done)
git checkout -b deployment

# Deploy current changes
git checkout deployment
git merge main
git push origin deployment

# View deployment status
# Go to: https://github.com/YOUR_USERNAME/song-remixer/actions
```
