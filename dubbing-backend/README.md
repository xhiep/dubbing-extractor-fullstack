# Dubbing Extractor - Backend

FastAPI + Celery backend for video processing with real-time WebSocket updates.

## Features

- REST API for video processing
- Celery background tasks
- WebSocket real-time progress updates
- Video download (yt-dlp)
- Transcription (Whisper)
- Translation (Google Translate)
- Subtitle burning (FFmpeg)
- Vietnamese TTS (VieNeu-TTS)

## Tech Stack

- FastAPI
- Celery + Redis
- Socket.IO (WebSocket)
- Whisper (OpenAI)
- FFmpeg
- VieNeu-TTS

## Quick Start

### Docker (Recommended)

```bash
docker-compose up
```

Access API: http://localhost:8000
API Docs: http://localhost:8000/docs

### Manual Setup

**Requirements:**
- Python 3.11+
- Redis

**Install:**
```bash
pip install -r requirements.txt
```

**Run:**
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Backend
./start_server.sh  # or start_server.bat on Windows

# Terminal 3: Celery Worker
./start_worker.sh  # or start_worker.bat on Windows
```

## API Endpoints

- `POST /api/process` - Start video processing
- `POST /api/preview` - Get video info
- `POST /api/tts/test` - Test TTS voice
- `GET /health` - Health check

## WebSocket Events

Connect to `/ws/socket.io`

**Client → Server:**
- `subscribe` - Subscribe to task updates

**Server → Client:**
- `progress` - Processing progress
- `log` - Log messages
- `completed` - Task completed
- `error` - Error occurred

## Environment Variables

Copy `.env.example` to `.env`:

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Project Structure

```
dubbing-backend/
├── app/
│   ├── api/           # REST endpoints
│   ├── core/          # Config
│   ├── models/        # Pydantic schemas
│   ├── main.py        # FastAPI app
│   ├── tasks.py       # Celery tasks
│   └── websocket.py   # Socket.IO handlers
├── src/               # Core modules
│   ├── modules/       # Video processing logic
│   └── utils/         # Helpers
├── bin/               # FFmpeg binaries
├── requirements.txt
└── docker-compose.yml
```

## License

MIT
