#!/bin/bash

# Song Remixer - Google Cloud Run Deployment Script
# This script deploys the app to Google Cloud Run (free tier eligible)

set -e

echo "🚀 Song Remixer - Google Cloud Deployment"
echo "=========================================="

# Configuration
PROJECT_ID="${GCLOUD_PROJECT_ID:-song-remixer}"
REGION="${GCLOUD_REGION:-us-central1}"
SERVICE_NAME="song-remixer"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Error: Not authenticated with gcloud"
    echo "Run: gcloud auth login"
    exit 1
fi

# Check for required environment variables
if [ -z "$REPLICATE_API_TOKEN" ]; then
    echo "⚠️  Warning: REPLICATE_API_TOKEN not set"
    echo "You'll need to set it in Cloud Run after deployment"
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY not set"
    echo "You'll need to set it in Cloud Run after deployment"
fi

if [ -z "$GENIUS_ACCESS_TOKEN" ]; then
    echo "⚠️  Warning: GENIUS_ACCESS_TOKEN not set"
    echo "You'll need to set it in Cloud Run after deployment"
fi

echo ""
echo "📋 Deployment Configuration:"
echo "   Project ID: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Service Name: $SERVICE_NAME"
echo "   Image: $IMAGE_NAME"
echo ""

# Prompt for confirmation
read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Set the project
echo "📦 Setting project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build the container
echo "🏗️  Building container image..."
gcloud builds submit --tag $IMAGE_NAME

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 600 \
    --max-instances 10 \
    --set-env-vars "FAST_MODE=true" \
    --set-env-vars "REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN:-}" \
    --set-env-vars "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}" \
    --set-env-vars "GENIUS_ACCESS_TOKEN=${GENIUS_ACCESS_TOKEN:-}"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo "✅ Deployment successful!"
echo "=========================================="
echo "🌐 Your app is live at: $SERVICE_URL"
echo ""
echo "📝 Next steps:"
echo "1. If you didn't set API keys, add them in Cloud Console:"
echo "   https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/variables"
echo ""
echo "2. Monitor logs:"
echo "   gcloud run logs tail $SERVICE_NAME --region $REGION"
echo ""
echo "3. Update deployment:"
echo "   ./deploy.sh"
echo ""
echo "💰 Cost estimate: Free tier includes 2M requests/month"
echo "=========================================="
