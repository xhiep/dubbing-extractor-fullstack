# Setup Troubleshooting Guide

## If setup.bat fails

### Try setup_quick.bat instead
```powershell
setup_quick.bat
```

This is a simpler version that:
- Only creates what's missing
- Skips if already setup
- Less error-prone

### Manual Setup

If both scripts fail, setup manually:

#### Backend
```powershell
cd dubbing-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-minimal.txt
copy .env.example .env
cd ..
```

#### Frontend
```powershell
cd dubbing-frontend
npm install
copy .env.example .env
cd ..
```

### Common Issues

**1. "Python not found"**
- Install Python 3.10+ from https://www.python.org/
- Make sure "Add to PATH" is checked during install

**2. "Node.js not found"**
- Install Node.js 18+ from https://nodejs.org/
- Restart terminal after install

**3. "pip install fails"**
```powershell
cd dubbing-backend
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\pip.exe install -r requirements-minimal.txt
```

**4. "npm install fails"**
```powershell
cd dubbing-frontend
npm cache clean --force
npm install
```

**5. "venv already exists"**
```powershell
cd dubbing-backend
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements-minimal.txt
```

**6. Script exits immediately**
- Run from Command Prompt (not PowerShell)
- Right-click setup.bat → "Run as Administrator"

### Check if setup worked

**Backend:**
```powershell
cd dubbing-backend
venv\Scripts\python.exe -c "import fastapi; print('OK')"
```

**Frontend:**
```powershell
cd dubbing-frontend
dir node_modules
```

### After successful setup

Run:
```powershell
start_all.bat
```

Or manually:
```powershell
# Terminal 1
cd dubbing-backend
venv\Scripts\activate
uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload

# Terminal 2
cd dubbing-frontend
npm run dev
```
