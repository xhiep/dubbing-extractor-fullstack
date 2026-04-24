# Dubbing Extractor - Full Stack Scripts

## Quick Start (3 Commands)

### First Time Setup
```powershell
cd C:\Users\xhiep\Downloads\dubbing-extractor-fullstack
setup.bat
```

This will:
1. Create Python venv
2. Install minimal backend dependencies
3. Install frontend npm packages
4. Create .env files

### Start All Services
```powershell
start_all.bat
```

Opens 2 terminal windows:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173

### Stop All Services
```powershell
stop_all.bat
```

Kills both backend and frontend processes.

## Scripts Overview

### `setup.bat` - First Time Setup
- Checks Python and Node.js installed
- Creates backend venv
- Installs minimal dependencies (10 packages, ~100MB)
- Installs frontend npm packages
- Creates .env files from examples

**Run once before first use.**

### `start_all.bat` - Start Both Services
- Starts backend (FastAPI + Uvicorn)
- Starts frontend (React + Vite)
- Opens 2 separate terminal windows
- Auto-checks if setup completed

**Run every time you want to develop.**

### `stop_all.bat` - Stop All Services
- Kills backend process
- Kills frontend process
- Closes terminal windows

**Run when you're done developing.**

## Usage Flow

### First Time
```powershell
# 1. Setup (once)
setup.bat

# 2. Start services
start_all.bat

# 3. Open browser
# http://localhost:5173
```

### Daily Development
```powershell
# Start
start_all.bat

# ... do your work ...

# Stop
stop_all.bat
```

## What Each Script Does

### setup.bat
```
[1/4] Setting up Backend
  - Create venv
  - Install requirements-minimal.txt

[2/4] Setting up Frontend
  - npm install

[3/4] Creating .env files
  - Copy .env.example → .env

[4/4] Setup complete!
```

### start_all.bat
```
[1/2] Starting Backend (FastAPI)
  - Opens new terminal: "Dubbing Backend"
  - Runs: uvicorn app.main:asgi_app --reload

[2/2] Starting Frontend (React + Vite)
  - Opens new terminal: "Dubbing Frontend"
  - Runs: npm run dev
```

### stop_all.bat
```
- Kills "Dubbing Backend" window
- Kills "Dubbing Frontend" window
```

## Terminal Windows

When you run `start_all.bat`, you'll see:

**Window 1: Dubbing Backend**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Window 2: Dubbing Frontend**
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

## Troubleshooting

### setup.bat fails

**Python not found:**
```
Install Python 3.10+ from https://www.python.org/
```

**Node.js not found:**
```
Install Node.js 18+ from https://nodejs.org/
```

### start_all.bat fails

**Backend venv not found:**
```powershell
cd dubbing-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-minimal.txt
```

**Frontend node_modules not found:**
```powershell
cd dubbing-frontend
npm install
```

### Port already in use

**Backend (8000):**
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Frontend (5173):**
```powershell
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

### Services won't stop

**Manual kill:**
```powershell
# Kill all Python processes
taskkill /IM python.exe /F

# Kill all Node processes
taskkill /IM node.exe /F
```

## File Structure

```
dubbing-extractor-fullstack/
├── setup.bat              ✅ First time setup
├── start_all.bat          ✅ Start both services
├── stop_all.bat           ✅ Stop all services
├── SCRIPTS_GUIDE.md       ✅ This file
├── dubbing-backend/
│   ├── start_dev.bat      ✅ Start backend only
│   └── requirements-minimal.txt
└── dubbing-frontend/
    └── package.json
```

## Advanced Usage

### Start Backend Only
```powershell
cd dubbing-backend
start_dev.bat
```

### Start Frontend Only
```powershell
cd dubbing-frontend
npm run dev
```

### Install Full Features
```powershell
cd dubbing-backend
venv\Scripts\activate
pip install -r requirements.txt
```

This installs:
- Whisper (transcription)
- VieNeu (TTS)
- yt-dlp (video download)
- All other features

**Warning:** ~5GB, 10 minutes

## Comparison

| Method | Setup Time | Services | Hot Reload |
|--------|-----------|----------|------------|
| Scripts | 2 min | Backend + Frontend | ✅ |
| Docker | 10 min | 5 services | ❌ |
| Manual | 5 min | Backend + Frontend | ✅ |

**Recommendation:** Use scripts for local dev, Docker for production.

## Summary

**3 scripts for easy development:**

1. `setup.bat` - Run once (first time)
2. `start_all.bat` - Run every time (daily dev)
3. `stop_all.bat` - Run when done

**Total setup time:** ~2 minutes
**Daily startup time:** ~5 seconds

No Docker needed for development!
