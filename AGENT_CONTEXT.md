# Agent Context

## Project
- Repo: `C:\Users\xhiep\Downloads\dubbing-extractor-fullstack`
- Remote: `https://github.com/xhiep/dubbing-extractor-fullstack.git`
- Main branch is used directly.
- This repo is a newer web/fullstack version inspired by:
  - old local repo: `C:\Users\xhiep\Downloads\dubbing-extractor`
  - VieNeu-TTS reference repo: `https://github.com/pnnbao97/VieNeu-TTS`

## User Priorities
- Preview on web must match backend render as closely as possible.
- `Source` tab and `Adjust` tab preview must be independent and both usable.
- User prefers real testing, not speculative fixes.
- Keep frontend/backend startup scripts aligned:
  - `stop_all.bat`
  - `start_all.bat`
  - `setup_full.bat`
- Keep UI consistent with `DESIGN.md`.
- Preserve responsive behavior.

## Current Preview Architecture
- Source preview metadata:
  - frontend `usePreview(source)` calls `/api/preview`
  - used for title, duration, width, height
- Real preview image/video:
  - backend endpoints in `dubbing-backend/app/api/preview_render.py`
  - `/api/preview-render/layout`
    - returns real backend-rendered frame image
    - includes subtitle band and subtitle layout
  - `/api/preview-render/render`
    - returns short preview video
- `AdjustTab` no longer depends on clicking preview in `SourceTab` first.
- `SourceTab` now also uses backend preview frame flow instead of only thumbnail display.

## Important Preview Rules
- Do not rely on browser-only subtitle simulation when exact alignment matters.
- Use backend-rendered frame/video whenever possible.
- Preview source clip should only be downloaded once per:
  - `source`
  - `start_time`
  - `duration`
- Changing blur/subtitle/font/layout options should reuse cached local preview source clip, not redownload from the link.

## Preview Cache / Storage Layout
- Persistent reference audio:
  - `storage/ref-audio`
- Preview source cache:
  - `storage/preview-source-cache`
- Preview rendered frames/videos:
  - `storage/preview-renders`
- Temp files:
  - `temp`

## Cleanup Behavior
- Cleanup API:
  - `POST /api/system/cleanup-storage`
- UI button:
  - header button `Don Cache/Temp`
- Cleanup should remove:
  - `temp`
  - `storage/preview-source-cache`
  - `storage/preview-renders`
  - legacy preview cache under `outputs/preview_sources`
  - legacy preview files under `outputs/previews`
- Cleanup should NOT remove:
  - `storage/ref-audio`

## Reference Audio Rules
- User wants reference audio stored in stable project storage, not temp.
- Uploaded clone voice files go through:
  - `POST /api/tts/upload-ref-audio`
- Valid persisted reference audio must be under:
  - `storage/ref-audio`
- Paths under `temp` should no longer be treated as valid persisted ref audio.
- On app load:
  - frontend verifies `processingOptions.dub_ref_audio`
  - if missing or invalid, clear:
    - `dub_ref_audio`
    - `dub_ref_text`

## Key Frontend Files
- `dubbing-frontend/src/App.jsx`
- `dubbing-frontend/src/components/SourceTab.jsx`
- `dubbing-frontend/src/components/AdjustTab.jsx`
- `dubbing-frontend/src/components/DubTab.jsx`
- `dubbing-frontend/src/components/PreviewCanvas.jsx`
- `dubbing-frontend/src/api/client.js`
- `dubbing-frontend/src/store/appStore.js`

## Key Backend Files
- `dubbing-backend/app/api/preview_render.py`
- `dubbing-backend/app/api/tts.py`
- `dubbing-backend/app/api/system.py`
- `dubbing-backend/app/core/config.py`
- `dubbing-backend/app/main.py`

## Current Preview UX Defaults
- Source tab backend preview:
  - start around `1s`
  - duration `3s`
- Adjust tab:
  - default start `1s`
  - default duration `5s`
  - UI currently constrains quick preview clip around `3-8s`
- Timeline preview is used to pick the preview moment.

## Known Technical Direction
- Exact 1:1 preview/render is only realistically achievable via backend-rendered preview artifacts.
- If preview mismatch returns again:
  - inspect backend subtitle layout values first
  - inspect actual rendered frame extraction path second
  - avoid reintroducing browser-only visual approximation

## TTS / Dub Notes
- VieNeu-TTS status bug was previously fixed around `ttsAPI.checkStatus`.
- Clone voice flow depends on:
  - `dub_ref_audio`
  - `dub_ref_text`
  - `dub_voice_volume`
  - `dub_source_volume`
  - `dub_mix_mode`
- Render/output speed semantics matter:
  - `render_video_speed` affects cover + subtitle timing + dubbing timeline
  - `output_video_speed` is final exported video speed relative to original

## Flow Audit Summary
- `SourceTab preview`
  - uses backend `/api/preview` for metadata
  - uses `/api/preview-render/layout` for real frame preview
  - only uses source/layout-related options
  - forces:
    - `cover_mode = none`
    - `burn_subtitle = false`
    - `render_video_speed = 1.0`
    - `video_speed = 1.0`
  - does not use:
    - whisper settings
    - subtitle timing scale/offset
    - dubbing settings
    - output format
- `AdjustTab render preview`
  - uses `/api/preview-render/layout` then `/api/preview-render/render`
  - uses cover/subtitle/layout/timeline options
  - does not run Whisper or dubbing
  - does not reflect full output container behavior
  - `output_video_speed` is only partially represented compared with full render
- `Step-by-step`
  - sends full `processingOptions` inside `step_data.options`
  - each step only consumes the relevant subset
  - step 3 produces editable SRT
  - steps 6-7 are where `output_format` matters most
  - step 7 is where dub settings matter most
- `Full render`
  - `/api/process/` is the most complete end-to-end option path
  - currently the best flow for checking true frontend/backend sync

## Option Matrix Notes
- Fully wired end-to-end in current code:
  - `whisper_model`
  - `whisper_language`
  - `cover_mode`
  - `cover_strength`
  - `burn_subtitle`
  - `srt_max_chars_per_line`
  - `subtitle_font_scale`
  - `subtitle_font_size`
  - `subtitle_margin_px`
  - `subtitle_timing_scale`
  - `subtitle_offset_sec`
  - `blur_padding_px`
  - `cover_offset_px`
  - `locked_subtitle_top_y`
  - `locked_subtitle_bottom_y`
  - `render_video_speed`
  - `output_video_speed`
  - `output_format`
  - all current dubbing options
- Legacy / special handling:
  - `video_speed` is now mostly a fallback alias
  - `mode` is flow-selection state, not a media-processing option
  - `source` is passed separately into backend process functions
  - `tts_voice` in backend schema is legacy and not used by current frontend dubbing flow

## Latest Sync Fixes
- Monolithic full render progress now emits real step progress instead of staying at `0.0%`
- Whisper model/language selected in UI now override backend defaults during actual transcription
- Output format selected in UI now affects final exported container (`mp4` / `mkv` / `webm`)
- Process result picking prefers finalized output files instead of stale `.mp4` intermediates
- Runtime directories now ignored in git:
  - `dubbing-backend/outputs/`
  - `storage/`

## Startup / Testing
- Stop all:
  - `cmd /c stop_all.bat`
- Start all:
  - `cmd /c start_all.bat`
- Frontend build:
  - `cmd /c npm run build` in `dubbing-frontend`
- Backend health:
  - `http://127.0.0.1:8000/health`

## Commits Worth Knowing
- `de7a9b2` decoupled source and adjust backend previews
- `baf61d6` cache preview source clips by source range
- `75cf68a` add cache and temp cleanup controls
- `49d3d1e` improve dubbing mix with smart ducking
- `779127c` show smart ducking mix mode in dub ui
- `a3424e4` sync dub request fields and mix defaults
- `d1a430b` restore monolithic progress sync
- `2d4dfe3` sync whisper overrides and output format
- `6b17153` ignore runtime output directories

## Git / Workspace Notes
- Repo may contain runtime folders not meant for commit:
  - `outputs/`
  - `dubbing-backend/outputs/`
- Be careful not to commit runtime cache/output by accident.
- Use `apply_patch` for manual edits.
- Do not revert unrelated user changes.

## What To Read First Next Time
1. This file
2. `DESIGN.md`
3. `dubbing-frontend/src/components/SourceTab.jsx`
4. `dubbing-frontend/src/components/AdjustTab.jsx`
5. `dubbing-backend/app/api/preview_render.py`
