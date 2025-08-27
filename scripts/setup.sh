#!/bin/bash

# Protectogram Development Setup Script

set -e

echo "🚀 Setting up Protectogram development environment..."

# Check if Python 3.12+ is available
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.12"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.12+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.bashrc
fi

echo "✅ uv is installed"

# Install dependencies
echo "📦 Installing dependencies..."
uv pip install -r requirements.txt
uv pip install -e ".[dev]"

# Setup pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp env.example .env
    echo "⚠️  Please edit .env with your configuration"
else
    echo "✅ .env already exists"
fi

# Create logs directory
mkdir -p logs

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your configuration"
echo "2. Run 'make test' to verify everything works"
echo "3. Run 'uvicorn app.main:app --reload' to start development server"
