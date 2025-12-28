#!/bin/bash

# Echo Backend - Quick Start Script

echo "🚀 Starting Echo Backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create a .env file with your GEMINI_API_KEY"
    echo ""
    echo "Example:"
    echo "  GEMINI_API_KEY=your_api_key_here"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Run server
echo "✅ Starting server on http://localhost:8000"
echo ""
python main.py

