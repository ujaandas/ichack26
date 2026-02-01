#!/bin/bash
# Frontend service startup script for Railway

# Exit on error
set -e

echo "🚀 Starting Frontend Service..."

# Install pnpm if not available
if ! command -v pnpm &> /dev/null; then
    echo "📦 Installing pnpm..."
    npm install -g pnpm
fi

# Install dependencies
echo "📦 Installing Node dependencies..."
pnpm install --frozen-lockfile

# Build for production
echo "🔨 Building frontend..."
pnpm build

# Serve the built files
echo "✅ Starting production server on port ${PORT:-5173}..."
pnpm preview --host 0.0.0.0 --port ${PORT:-5173}
