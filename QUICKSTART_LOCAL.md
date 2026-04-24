# Quick Start - Local Development (No Docker)

## Backend Setup

```powershell
cd dubbing-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-minimal.txt
start_dev.bat
```

Server: http://localhost:8000

## Frontend Setup

```powershell
cd dubbing-frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## What's Installed (Minimal)

**Backend:**
- FastAPI + Uvicorn (web server)
- python-socketio (WebSocket)
- aiohttp (HTTP client)
- pydantic (validation)

**Heavy dependencies NOT installed:**
- ❌ Whisper (transcription)
- ❌ Torch (ML models)
- ❌ VieNeu (TTS)
- ❌ yt-dlp (video download)

Install them later when needed:
```powershell
pip install openai-whisper yt-dlp deep-translator vieneu
```

## Files Added

- `requirements-minimal.txt` - Minimal dependencies (10 packages)
- `start_dev.bat` - Quick start script
- `README_LOCAL_DEV.md` - Local dev guide

## Full Setup (All Features)

If you need all features:
```powershell
pip install -r requirements.txt
```

**Warning:** Installs 100+ packages (~5GB)
