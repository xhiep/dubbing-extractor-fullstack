# Agent Context

## Project
- Repo: `dubbing-extractor-fullstack`
- Purpose: web version of the old `dubbing-extractor` app for download/transcribe/translate/cover/burn subtitle/dub workflows.
- Frontend: React + Vite + Zustand + React Query + Tailwind.
- Backend: FastAPI + Socket.IO + Python workflow modules under `dubbing-backend/src/modules`.

## Current UI Direction
- Follow `DESIGN.md`: restrained Apple-like neutral surfaces, blue only for actions/signals.
- Dark/light theme exists at frontend root via `theme-light` / `theme-dark`.
- Shared CSS helpers already added in `dubbing-frontend/src/index.css`:
  - `surface-subtle`
  - `option-card`
  - `notice-info`
  - `notice-error`
  - `notice-warning`

## Important Functional Context
- Preview render in Adjust tab was fixed to use backend-rendered preview video and same-origin websocket/proxy behavior.
- Adjust tab now prefers a desktop 2-column layout:
  - left: preview/video/timeline/preview text
  - right: stacked controls
  - responsive fallback: auto-stack into 1 column on narrow widths
- VieNeu-TTS status bug was fixed by syncing frontend API client with backend endpoints.
- Step-by-step mode is being aligned with the old repo:
  - user can choose a target step directly
  - backend should auto-run missing prerequisites
  - editable SRT appears after translation step
  - later steps should use edited SRT if saved
  - state is stored in `pipeline_state.json` inside each step-task workspace under `dubbing-backend/output/<task_id>/`

## Files To Check First Next Time
- Frontend
  - `dubbing-frontend/src/components/StepByStepPanel.jsx`
  - `dubbing-frontend/src/components/SourceTab.jsx`
  - `dubbing-frontend/src/components/AdjustTab.jsx`
  - `dubbing-frontend/src/components/DubTab.jsx`
  - `dubbing-frontend/src/api/client.js`
  - `dubbing-frontend/src/store/appStore.js`
  - `dubbing-frontend/src/index.css`
- Backend
  - `dubbing-backend/app/api/process.py`
  - `dubbing-backend/app/tasks.py`
  - `dubbing-backend/src/modules/workflow.py`
  - `dubbing-backend/src/modules/transcription/srt_generator.py`

## Verified Behaviors
- Running target step 3 via `/api/process/step/3` auto-completes missing prerequisites and returns `srt_content`.
- `/api/process/step-srt/{task_id}` supports save/reload for edited SRT.
- Running target step 5 after editing SRT keeps the edited subtitle content in outputs.

## Scripts
- `setup_full.bat`: install/setup full environment
- `start_all.bat`: stop old processes, then start backend/frontend
- `stop_all.bat`: kill frontend/backend related processes

## Old Repo Reference
- Old desktop repo path on this machine:
  - `C:\Users\xhiep\Downloads\dubbing-extractor`
- Use it as feature parity reference, especially for:
  - step-by-step pipeline behavior
  - SRT editing after translation
  - preview subtitle dragging/timeline/cover alignment

## Working Notes
- Do not revert unrelated user changes; worktree may already be dirty.
- Prefer keeping frontend strings in clean UTF-8 Vietnamese; mojibake happened before.
- When step-by-step behavior changes, test both backend endpoints and UI flow, not just build.
