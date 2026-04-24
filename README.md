# Dubbing Extractor - Full Stack Web Application

**Modern video dubbing and subtitle extraction tool with web interface.**

## 🚀 Quick Start

### Option 1: Full Setup (Recommended)
```powershell
# Install everything (PyTorch, Whisper, yt-dlp)
setup_full.bat

# Copy FFmpeg binaries (REQUIRED)
copy ..\dubbing-extractor\bin\ffmpeg\*.exe dubbing-backend\bin\ffmpeg\

# Start services
start_all.bat
```

### Option 2: Minimal Setup
```powershell
# Install core dependencies only
setup.bat

# Copy FFmpeg binaries (REQUIRED)
copy ..\dubbing-extractor\bin\ffmpeg\*.exe dubbing-backend\bin\ffmpeg\

# Start services
start_all.bat
```

### Check Environment
```powershell
# Verify all dependencies are installed
check_env.bat
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Stop Services
```powershell
stop_all.bat
```

## 📋 Features

### Video Processing Pipeline
1. **Download** - YouTube/local video (yt-dlp)
2. **Transcribe** - Speech-to-text (Whisper)
3. **Translate** - Vietnamese translation (Google Translate)
4. **Subtitle** - Generate SRT files (original, translated, bilingual)
5. **Burn** - Embed subtitles into video (FFmpeg)
6. **Dub** - Vietnamese voice-over (VieNeu-TTS)

### Web Interface
- **Source Tab** - Input video URL or upload
- **Adjust Tab** - Configure processing options
- **Dub Tab** - TTS voice settings and preview
- **Log Tab** - Real-time processing logs

### Real-time Updates
- WebSocket connection for live progress
- Toast notifications
- Progress bar with step tracking

## 🛠️ Tech Stack

**Backend:**
- FastAPI (REST API)
- Celery (background tasks)
- Socket.IO (WebSocket)
- Whisper (transcription)
- VieNeu-TTS (Vietnamese dubbing)
- FFmpeg (video processing)

**Frontend:**
- React 18
- Vite
- TailwindCSS
- Zustand (state management)
- Socket.IO (WebSocket)

## 📁 Project Structure

```
dubbing-extractor-fullstack/
├── setup.bat                    # First time setup
├── start_all.bat                # Start both services
├── stop_all.bat                 # Stop all services
├── SCRIPTS_GUIDE.md             # Scripts documentation
├── QUICKSTART_LOCAL.md          # Quick start guide
├── dubbing-backend/             # FastAPI backend
│   ├── app/                     # API routes, tasks, websocket
│   ├── src/                     # Core modules (27 files)
│   ├── bin/ffmpeg/              # FFmpeg binaries
│   ├── requirements.txt         # Full dependencies (100+)
│   ├── requirements-minimal.txt # Minimal dependencies (10)
│   ├── start_dev.bat            # Start backend only
│   └── README_LOCAL_DEV.md      # Local dev guide
└── dubbing-frontend/            # React frontend
    ├── src/                     # Components, hooks, store
    ├── package.json             # Node dependencies
    └── README.md                # Frontend docs
```

## 🔧 Configuration

### Backend (.env)
```bash
cd dubbing-backend
cp .env.example .env
```

Edit `.env`:
- `WHISPER_MODEL` - Transcription model (tiny/base/small/medium/large)
- `TARGET_LANGUAGE` - Translation target (default: vi)
- `ENABLE_DUB` - Enable Vietnamese TTS dubbing
- `OUTPUT_DIR` - Output directory

### Frontend (.env)
```bash
cd dubbing-frontend
cp .env.example .env
```

Edit `.env`:
- `VITE_API_URL` - Backend API URL (default: http://localhost:8000)

## 📦 Installation Options

### Option 1: Minimal (Recommended for Dev)
```powershell
setup.bat
```

**Installs:**
- FastAPI + Uvicorn (web server)
- Socket.IO (WebSocket)
- Basic dependencies

**Size:** ~100 MB
**Time:** ~2 minutes
**Features:** Server only (no video processing)

### Option 2: Full Features
```powershell
cd dubbing-backend
venv\Scripts\activate
pip install -r requirements.txt
```

**Installs:**
- All minimal dependencies
- Whisper (transcription)
- VieNeu-TTS (dubbing)
- yt-dlp (video download)
- All processing features

**Size:** ~5 GB
**Time:** ~10 minutes
**Features:** Complete video processing

## 🎯 Development Workflow

### Daily Development
```powershell
# Start services
start_all.bat

# Edit code (hot reload enabled)
# - Backend: app/api/*.py
# - Frontend: src/**/*.jsx

# Stop services
stop_all.bat
```

### Add Features as Needed
```powershell
cd dubbing-backend
venv\Scripts\activate

# Video download
pip install yt-dlp

# Transcription
pip install openai-whisper torch

# Translation
pip install deep-translator

# TTS
pip install vieneu
```

## 🐳 Docker Deployment (Production)

```powershell
docker-compose up -d
```

**Services:**
- redis (message broker)
- backend (FastAPI)
- worker (Celery)
- frontend (React)
- nginx (reverse proxy)

See `docker-compose.yml` for details.

## 📚 Documentation

- [Scripts Guide](SCRIPTS_GUIDE.md) - setup.bat, start_all.bat, stop_all.bat
- [Quick Start Local](QUICKSTART_LOCAL.md) - Local dev without Docker
- [Backend Local Dev](dubbing-backend/README_LOCAL_DEV.md) - Backend setup
- [Backend README](dubbing-backend/README.md) - Backend architecture
- [Frontend README](dubbing-frontend/README.md) - Frontend architecture

## 🔍 API Endpoints

### REST API
- `GET /health` - Health check
- `POST /api/process` - Start video processing
- `POST /api/preview` - Get video info
- `POST /api/tts/test` - Test TTS voice

### WebSocket
- Connect to: `ws://localhost:8000/ws/socket.io`
- Real-time progress updates

## 🐛 Troubleshooting

### Services won't start

**Check Python:**
```powershell
python --version  # Need 3.10+
```

**Check Node.js:**
```powershell
node --version  # Need 18+
```

**Re-run setup:**
```powershell
setup.bat
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

### Import errors

**Install missing package:**
```powershell
cd dubbing-backend
venv\Scripts\activate
pip install <package-name>
```

## 📊 Comparison

| Method | Setup | Size | Time | Hot Reload | Production |
|--------|-------|------|------|------------|------------|
| Scripts (Minimal) | ✅ | 100 MB | 2 min | ✅ | ❌ |
| Scripts (Full) | ✅ | 5 GB | 10 min | ✅ | ❌ |
| Docker | ✅ | 8 GB | 15 min | ❌ | ✅ |

**Recommendation:**
- Development: Use scripts (minimal)
- Production: Use Docker

## 📝 License

MIT

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test locally with `start_all.bat`
5. Submit pull request

## 📞 Support

- Issues: GitHub Issues
- Documentation: See `/docs` folder
- Scripts: See `SCRIPTS_GUIDE.md`

---

**Made with ❤️ for Vietnamese content creators**
