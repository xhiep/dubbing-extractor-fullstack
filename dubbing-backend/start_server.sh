#!/bin/bash
# Start FastAPI server with uvicorn

cd "$(dirname "$0")"

# Activate venv (use parent venv with all dependencies)
source ../venv/Scripts/activate

# Install backend-specific dependencies
pip install -q -r requirements.txt

# Start uvicorn
uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload
