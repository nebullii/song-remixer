#!/bin/bash

# Setup script for GitHub Actions deployment
# This creates a Google Cloud service account for GitHub Actions

set -e

echo "🔧 Setting up GitHub Actions Deployment"
echo "========================================"
echo ""

# Configuration
PROJECT_ID="glassy-keyword-474117-j6"
SA_NAME="github-actions"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="github-actions-key.json"

echo "📋 Configuration:"
echo "   Project: $PROJECT_ID"
echo "   Service Account: $SA_EMAIL"
echo ""

# Check if already exists
if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    echo "⚠️  Service account already exists"
    read -p "Do you want to create a new key? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping service account creation"
        SKIP_SA=true
    fi
fi

if [ "$SKIP_SA" != "true" ]; then
    echo "1️⃣  Creating service account..."
    gcloud iam service-accounts create $SA_NAME \
        --display-name="GitHub Actions Deployer" \
        --project=$PROJECT_ID 2>/dev/null || echo "   (already exists)"

    echo "2️⃣  Granting permissions..."
    
    # Cloud Run Admin
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/run.admin" \
        --condition=None \
        --quiet

    # Storage Admin (for Container Registry)
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/storage.admin" \
        --condition=None \
        --quiet

    # Service Account User
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/iam.serviceAccountUser" \
        --condition=None \
        --quiet

    echo "   ✅ Permissions granted"
fi

echo "3️⃣  Creating service account key..."
gcloud iam service-accounts keys create $KEY_FILE \
    --iam-account=$SA_EMAIL \
    --project=$PROJECT_ID

echo "   ✅ Key created: $KEY_FILE"
echo ""

echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Go to your GitHub repository:"
echo "   Settings → Secrets and variables → Actions"
echo ""
echo "2. Add these secrets:"
echo ""
echo "   Secret: GCP_SA_KEY"
echo "   Value: (copy the entire contents below)"
echo ""
echo "---BEGIN KEY---"
cat $KEY_FILE
echo "---END KEY---"
echo ""
echo "   Secret: REPLICATE_API_TOKEN"
echo "   Value: (from your .env file)"
echo ""
echo "   Secret: ANTHROPIC_API_KEY"
echo "   Value: (from your .env file)"
echo ""
echo "   Secret: GENIUS_ACCESS_TOKEN"
echo "   Value: (from your .env file)"
echo ""
echo "3. Push to deployment branch:"
echo "   git push origin deployment"
echo ""
echo "⚠️  IMPORTANT: Delete the key file after copying:"
echo "   rm $KEY_FILE"
echo ""
echo "========================================"
