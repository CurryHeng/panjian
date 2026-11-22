# Panjian local clipping Implementation Plan

> **For agentic workers:** Execute inline with executing-plans, test-driven-development and verification-before-completion. Steps use checkbox syntax.

**Goal:** Build a runnable local video selection and MP4 export workflow.

**Architecture:** FastAPI serves a same-origin local editing interface. File-backed projects and background export tasks call a small FFmpeg media module.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, python-multipart, imageio-ffmpeg; browser JavaScript.

## Global Constraints
- Bind only 127.0.0.1; no public deployment or model API calls.
- Keep source footage unchanged; store generated data under data/.
- No simulated AI results. Manual selections must be labeled as manual.
- Source duration bounds all clips; background exports preserve selection order.

## Task 1: Real video import and validation
Files: app/media.py, app/main.py, tests/test_workflow.py.
Produces: create_app(data_dir), GET /api/projects, POST /api/projects multipart file, GET /api/projects/{id}.
- [x] Write integration tests creating a 6-second synthetic video with imageio-ffmpeg, importing it, and rejecting non-video bytes.
- [x] Run `python -m pytest -q` and confirm missing workflow fails.
- [x] Implement FFmpeg probe, bounded streaming upload and file-backed metadata.
- [x] Run the import tests and confirm duration and rejection behavior.

## Task 2: Persistent editable selections
Files: app/main.py, tests/test_workflow.py.
Consumes: project duration. Produces: PUT /api/projects/{id}/clips with {clips:[{id,start,end,title,notes}]}.
- [x] Test valid edits survive a fresh app instance; invalid, non-finite and out-of-range intervals return 422.
- [x] Implement validated models and atomic JSON writes.
- [x] Run workflow tests.

## Task 3: Ordered background exports
Files: app/media.py, app/main.py, tests/test_workflow.py.
Consumes: saved clip list. Produces POST /api/projects/{id}/exports, GET /api/jobs/{id}, GET /api/exports/{id}.
- [x] Test two reordered clips yield a decodable MP4 of expected duration and expected opening frame color, with and without audio.
- [x] Implement sequential re-encoding, concatenation, task persistence and bounded errors.
- [x] Run complete workflow tests; reject empty export and unknown IDs.

## Task 4: Local editing interface and delivery
Files: app/static/index.html, app/static/style.css, app/static/app.js, README.md, start.ps1.
- [x] Build video upload/player, manual clip controls, reorder buttons and export status UI.
- [x] Syntax-check JavaScript; run live HTTP smoke check and backend test suite.
- [x] Update TODO.md with verified completions and record remaining AI/Android work.
