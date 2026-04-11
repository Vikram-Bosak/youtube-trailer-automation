#!/bin/bash
# =============================================
# YouTube Trailer Automation - Setup Script
# =============================================

echo "================================================"
echo "  YouTube Trailer Automation - Setup"
echo "================================================"
echo ""

# Check Python
echo "🔍 Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "❌ Python not found! Please install Python 3.9+"
    exit 1
fi
echo "✅ Python found: $($PYTHON --version)"

# Check FFmpeg
echo ""
echo "🔍 Checking FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg found: $(ffmpeg -version | head -1)"
else
    echo "❌ FFmpeg not found! Please install FFmpeg"
    echo "   Ubuntu/Debian: sudo apt install ffmpeg"
    echo "   macOS: brew install ffmpeg"
    echo "   Windows: choco install ffmpeg"
    exit 1
fi

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
$PYTHON -m venv venv
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install yt-dlp
echo ""
echo "📦 Updating yt-dlp..."
pip install --upgrade yt-dlp

# Create .env if not exists
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your actual credentials!"
fi

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p downloads processed backups logs data

echo ""
echo "================================================"
echo "  ✅ Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Place client_secrets.json in the project root"
echo "  3. Run: python scripts/generate_oauth_token.py"
echo "  4. Run: python main.py --once  (single run)"
echo "  5. Run: python main.py         (continuous)"
echo ""
