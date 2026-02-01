#!/bin/bash
# Backend service startup script for Railway

# Exit on error
set -e

echo "🚀 Starting Backend Service..."

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Installing Python dependencies..."
    pip install --no-cache-dir -r requirements.txt
fi

# Start the FastAPI application
echo "✅ Starting uvicorn server on port ${PORT:-8001}..."
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001} --workers 2
