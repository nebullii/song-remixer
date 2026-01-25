#!/bin/bash

# Pre-deployment verification script
# Run this before deploying to check if everything is ready

echo "🔍 Song Remixer - Pre-Deployment Check"
echo "======================================"
echo ""

ERRORS=0
WARNINGS=0

# Check gcloud installation
echo "Checking gcloud CLI..."
if command -v gcloud >/dev/null 2>&1; then
    echo "  ✅ gcloud installed: $(gcloud --version | head -n1)"
else
    echo "  ❌ gcloud not installed"
    echo "     Install: brew install --cask google-cloud-sdk"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check authentication
echo "Checking authentication..."
if gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
    ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    echo "  ✅ Authenticated as: $ACCOUNT"
else
    echo "  ❌ Not authenticated"
    echo "     Run: gcloud auth login"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check project
echo "Checking project..."
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -n "$PROJECT" ]; then
    echo "  ✅ Project set: $PROJECT"
else
    echo "  ❌ No project set"
    echo "     Run: gcloud config set project YOUR_PROJECT_ID"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check API keys
echo "Checking API keys..."
if [ -f .env ]; then
    source .env
    
    if [ -n "$REPLICATE_API_TOKEN" ]; then
        echo "  ✅ REPLICATE_API_TOKEN set"
    else
        echo "  ⚠️  REPLICATE_API_TOKEN not set in .env"
        echo "     Get one at: https://replicate.com/account/api-tokens"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "  ✅ ANTHROPIC_API_KEY set"
    else
        echo "  ⚠️  ANTHROPIC_API_KEY not set in .env"
        echo "     Get one at: https://console.anthropic.com/"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    if [ -n "$GENIUS_ACCESS_TOKEN" ]; then
        echo "  ✅ GENIUS_ACCESS_TOKEN set"
    else
        echo "  ⚠️  GENIUS_ACCESS_TOKEN not set in .env"
        echo "     Get one at: https://genius.com/api-clients"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "  ⚠️  .env file not found"
    echo "     Copy .env.example to .env and add your API keys"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Check Docker (optional)
echo "Checking Docker (optional)..."
if command -v docker >/dev/null 2>&1; then
    echo "  ✅ Docker installed: $(docker --version)"
    
    # Check if Docker is running
    if docker ps >/dev/null 2>&1; then
        echo "  ✅ Docker daemon running"
    else
        echo "  ⚠️  Docker daemon not running"
        echo "     Start Docker Desktop"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "  ⚠️  Docker not installed (optional for local testing)"
    echo "     Install: brew install --cask docker"
fi
echo ""

# Check required files
echo "Checking required files..."
REQUIRED_FILES=("Dockerfile" "deploy.sh" "requirements.txt" "app.py")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file exists"
    else
        echo "  ❌ $file missing"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# Summary
echo "======================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✅ All checks passed! Ready to deploy."
    echo ""
    echo "Run: ./deploy.sh"
elif [ $ERRORS -eq 0 ]; then
    echo "⚠️  $WARNINGS warning(s) found."
    echo "You can proceed, but you may need to set API keys after deployment."
    echo ""
    echo "Run: ./deploy.sh"
else
    echo "❌ $ERRORS error(s) found. Please fix before deploying."
    if [ $WARNINGS -gt 0 ]; then
        echo "⚠️  $WARNINGS warning(s) also found."
    fi
    exit 1
fi
echo "======================================"
