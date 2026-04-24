# Dubbing Extractor - Frontend

React + Vite frontend for video processing with real-time updates.

## Features

- Modern React 18 UI
- Real-time WebSocket updates
- 4 tabs: Source, Adjust, Dub, Log
- Progress tracking
- Toast notifications
- Responsive design with TailwindCSS

## Tech Stack

- React 18
- Vite
- TailwindCSS
- Zustand (state management)
- Socket.IO (WebSocket)
- Axios (HTTP client)

## Quick Start

### Install Dependencies

```bash
npm install
```

### Development

```bash
npm run dev
```

Access: http://localhost:5173

### Build for Production

```bash
npm run build
```

Output: `dist/`

### Preview Production Build

```bash
npm run preview
```

## Environment Variables

Create `.env` file:

```bash
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
dubbing-frontend/
├── src/
│   ├── components/        # UI components
│   │   ├── SourceTab.jsx
│   │   ├── AdjustTab.jsx
│   │   ├── DubTab.jsx
│   │   ├── LogTab.jsx
│   │   ├── ProgressBar.jsx
│   │   └── StatusBar.jsx
│   ├── hooks/             # Custom hooks
│   │   ├── useWebSocket.js
│   │   └── useProcessing.js
│   ├── store/             # Zustand store
│   │   └── appStore.js
│   ├── api/               # API client
│   │   └── client.js
│   ├── App.jsx
│   └── main.jsx
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## API Integration

Frontend connects to backend API at `VITE_API_URL` (default: http://localhost:8000)

**REST Endpoints:**
- `POST /api/process` - Start processing
- `POST /api/preview` - Get video info
- `POST /api/tts/test` - Test TTS

**WebSocket:**
- Connect to `/ws/socket.io`
- Real-time progress updates

## Development

### Hot Module Replacement

Vite provides instant HMR for fast development.

### State Management

Uses Zustand for global state:
- Processing status
- Progress tracking
- Log messages
- Configuration

### WebSocket Connection

Automatic reconnection on disconnect.
Subscribe to task updates for real-time progress.

## License

MIT
