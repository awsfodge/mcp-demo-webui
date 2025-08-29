#!/bin/bash

# MCP Demo Standalone - Run Script

echo "==================================="
echo "MCP Demo Standalone Application"
echo "==================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your configuration."
    echo ""
fi

# Create necessary directories
mkdir -p data logs flask_session

# Run the application
echo ""
echo "Starting MCP Demo on http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""
python app.py