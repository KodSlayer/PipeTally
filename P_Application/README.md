# BirlaNu_V2 — Developer README

Short developer-focused guide for the BirlaNu_V2 project (backend + frontend).

## Project Overview

- Structure: two services — `Backend` (FastAPI) and `Frontend` (Streamlit).

## Repo Layout

- `Backend/` — FastAPI app, model artifacts, and utility pipelines.
  - `main.py` — FastAPI application entrypoint.
  - `routers/` — API routers (e.g., `detection.py`).
  - `Utils/` — model weights and pipeline helpers (`hybrid_pipeline.py`, `single_pipes.py`, `model_cache.py`).
  - `database/` — DB connection and models.
- `Frontend/` — Streamlit UI and related assets.
- `docker-compose.yml` — Ignore docker-compose file as of now!!

## Requirements

- Python 3.9+ recommended.
- See `Backend/requirements.txt` and `Frontend/requirements.txt` for exact packages.


## Running locally without Docker

python -m venv .venv
.\.venv\Scripts\activate

Backend (development):

```bash
cd Backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (development):

```bash
cd Frontend
pip install -r requirements.txt
streamlit run streamlit.py
```

## Developer notes

- Model artifacts: large files live in `Backend/Utils` (e.g., `crop_yolo26.pt`, `maskrcnn_pipeV4.pth`). Do not check these into a remote repo unless intended.
- Cache and loading: `Backend/Utils/model_cache.py` contains helpers for caching model instances — reuse to avoid reloading during requests.
- API routes: `Backend/routers/detection.py` shows typical detection request/response shape.
- Database: `Backend/database/database.py` and `models/database_models.py` handle persistence — update migrations or schema as needed.


## Backend Endpoints

The detection API is mounted under the `/detect` prefix (see `Backend/routers/detection.py`). Key endpoints:

- **POST** `/detect/stacked` — Hybrid pipeline (Mask R-CNN -> YOLO) for stacked/bundled pipes.
  - Payload: `multipart/form-data` with a file field named `file` (image).
  - Response: JSON with `model`, `pipe_count`, `segments`, `detection_id`, and `image_base64` (annotated image).
  - Example:


- **POST** `/detect/single` — Lightweight Mask R-CNN endpoint for single (non-stacked) pipes.
  - Payload: `multipart/form-data` with `file` field.
  - Response: JSON with `model`, `pipe_count`, `detection_id`, and `image_base64`.
  - Example:


- **GET** `/detect/result/{detection_id}` — Fetch the annotated result image by `detection_id` (returns image bytes).

- **DELETE** `/detect/clear_data` — Clear stored detection records from the database.


## Troubleshooting

- If models fail to load, check available GPU drivers and CUDA versions (if using GPU builds).


