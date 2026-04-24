#!/bin/bash
# Start Celery worker

cd "$(dirname "$0")"

# Activate venv
source ../venv/Scripts/activate

# Start Celery worker
celery -A app.tasks:celery_app worker --loglevel=info --concurrency=2
