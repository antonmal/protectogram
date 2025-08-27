#!/bin/bash

# Protectogram Staging Deployment Script

set -e

echo "🚀 Deploying Protectogram to staging..."

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI is not installed. Please install it first."
    echo "Visit: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# Check if we're logged in to Fly
if ! fly auth whoami &> /dev/null; then
    echo "❌ Not logged in to Fly. Please run 'fly auth login' first."
    exit 1
fi

echo "✅ Fly CLI is ready"

# Check if app exists
if ! fly apps list | grep -q "protectogram-staging"; then
    echo "📦 Creating protectogram-staging app..."
    fly apps create protectogram-staging
else
    echo "✅ App protectogram-staging exists"
fi

# Check if Postgres database exists
if ! fly postgres list | grep -q "protectogram-pg-staging"; then
    echo "🗄️  Creating Postgres database..."
    fly postgres create protectogram-pg-staging
    echo "🔗 Attaching database to app..."
    fly postgres attach protectogram-pg-staging --app protectogram-staging
else
    echo "✅ Postgres database exists"
fi

# Build and deploy
echo "🏗️  Building and deploying..."
fly deploy --config fly.toml

# Check deployment status
echo "🔍 Checking deployment status..."
fly status --app protectogram-staging

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Set secrets: fly secrets set --app protectogram-staging"
echo "2. Configure webhooks for Telegram and Telnyx"
echo "3. Run smoke tests"
