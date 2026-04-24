# Dubbing Extractor Backend - Local Development Setup

## Quick Start (No Docker)

### 1. Create Virtual Environment

```powershell
cd C:\Users\xhiep\Downloads\dubbing-extractor-fullstack\dubbing-backend
python -m venv venv
venv\Scripts\activate
```

### 2. Install Minimal Dependencies

```powershell
pip install -r requirements-minimal.txt
```

This installs only:
- FastAPI + Uvicorn (web server)
- python-socketio (WebSocket)
- aiohttp (HTTP client)
- pydantic (validation)

**Heavy dependencies (whisper, torch, vieneu) are NOT installed yet.**

### 3. Run Server

```powershell
uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload
```

Server starts at: http://localhost:8000

### 4. Test Server

```powershell
# Health check
curl http://localhost:8000/health

# API docs
# Open browser: http://localhost:8000/docs
```

## Install Heavy Dependencies (When Needed)

### For Video Download
```powershell
pip install yt-dlp==2026.3.17
```

### For Transcription (Whisper)
```powershell
pip install openai-whisper==20250625
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

### For Translation
```powershell
pip install deep-translator==1.11.4
```

### For TTS (VieNeu)
```powershell
pip install vieneu==2.4.3
```

### For Video Processing (FFmpeg wrapper)
```powershell
pip install opencv-python-headless==4.13.0.92
```

## Full Installation (All Features)

If you want all features at once:

```powershell
pip install -r requirements.txt
```

**Warning:** This installs 100+ packages (~5GB). Only do this if you need all features.

## Project Structure

```
dubbing-backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── api/                 # API routes
│   │   ├── process.py       # Video processing endpoints
│   │   ├── preview.py       # Preview endpoints
│   │   └── tts.py           # TTS endpoints
│   ├── core/
│   │   └── config.py        # Configuration
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── tasks.py             # Celery tasks (optional)
│   └── websocket.py         # Socket.IO handlers
├── src/                     # Core modules
│   ├── modules/
│   │   ├── downloader/      # yt-dlp wrapper
│   │   ├── transcription/   # Whisper + translation
│   │   ├── tts/             # VieNeu-TTS
│   │   ├── video_processing/# FFmpeg wrapper
│   │   └── workflow.py      # Pipeline orchestration
│   └── utils/               # Utilities
├── bin/ffmpeg/              # FFmpeg binaries
├── requirements.txt         # Full dependencies
├── requirements-minimal.txt # Minimal dependencies (server only)
└── README_LOCAL_DEV.md      # This file
```

## Configuration

### Create .env file

```powershell
cp .env.example .env
```

Edit `.env`:
```bash
# Whisper Model (tiny, base, small, medium, large)
WHISPER_MODEL=base

# Target Language
TARGET_LANGUAGE=vi

# Output directory
OUTPUT_DIR=output

# Debug mode
DEBUG=true
```

## Development Workflow

### 1. Start with minimal setup
```powershell
pip install -r requirements-minimal.txt
uvicorn app.main:asgi_app --reload
```

### 2. Add features as needed
```powershell
# Need video download?
pip install yt-dlp

# Need transcription?
pip install openai-whisper torch

# Need TTS?
pip install vieneu
```

### 3. Hot reload enabled
- Edit code → server auto-reloads
- No need to restart manually

## API Endpoints

### Health Check
```
GET /health
```

### Video Processing
```
POST /api/process
Body: {
  "video_url": "https://youtube.com/watch?v=...",
  "options": {...}
}
```

### Preview Video Info
```
POST /api/preview
Body: {
  "video_url": "https://youtube.com/watch?v=..."
}
```

### Test TTS
```
POST /api/tts/test
Body: {
  "text": "Xin chào",
  "voice": "preset"
}
```

### WebSocket
```
Connect to: ws://localhost:8000/ws/socket.io
```

## Troubleshooting

### Server won't start

**Check Python version:**
```powershell
python --version  # Need 3.10+
```

**Check venv activated:**
```powershell
# Should see (venv) in prompt
venv\Scripts\activate
```

**Check dependencies installed:**
```powershell
pip list | findstr fastapi
```

### Import errors

**Missing module:**
```powershell
# Install the specific package
pip install <package-name>
```

**Wrong Python path:**
```powershell
# Make sure using venv Python
where python
# Should show: C:\Users\xhiep\Downloads\dubbing-extractor-fullstack\dubbing-backend\venv\Scripts\python.exe
```

### Port already in use

**Change port:**
```powershell
uvicorn app.main:asgi_app --port 8001 --reload
```

**Or kill existing process:**
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

## Production Deployment

For production, use Docker:

```powershell
docker-compose up -d
```

See main README.md for Docker setup.

## Comparison: Minimal vs Full

| Feature | Minimal | Full |
|---------|---------|------|
| Install time | ~30 seconds | ~10 minutes |
| Disk space | ~100 MB | ~5 GB |
| Packages | 10 | 100+ |
| Server only | ✅ | ✅ |
| Video download | ❌ | ✅ |
| Transcription | ❌ | ✅ |
| Translation | ❌ | ✅ |
| TTS | ❌ | ✅ |
| Video processing | ❌ | ✅ |

**Recommendation:** Start with minimal, add features as needed.
