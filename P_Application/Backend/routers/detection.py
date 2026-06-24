from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from models.database_models import DetectionResult
from Utils.hybrid_pipeline import run_hybrid_pipeline_cached
from Utils.single_pipes import run_single_pipes_pipeline_cached
from Utils.model_cache import get_models, inference_semaphore
import base64
import tempfile
import shutil
import os

router = APIRouter(prefix="/detect", tags=["Detection"])


def encode_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def save_to_db(db, model_used, image_name, pipe_count, confidence=None):
    record = DetectionResult(
        model_used=model_used,
        image_name=image_name,
        pipe_count=pipe_count,
        confidence=confidence
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── Unified hybrid pipeline (Mask R-CNN + YOLO) ───────────────────────────────
@router.post("/stacked")
def detect_pipe(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Single endpoint for both single and stacked pipe images.
    Internally uses the hybrid pipeline:
      Stage 1 — Mask R-CNN  : segments pipe bundles
      Stage 2 — YOLO        : counts inner pipes per segment
    Returns pipe_count (total inner pipes) and segments count.
    """
    suffix = os.path.splitext(file.filename)[-1] or ".jpg"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
        shutil.copyfileobj(file.file, tmp_in)
        input_path = tmp_in.name

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_out:
        output_path = tmp_out.name

    try:
        # Only one inference at a time — prevents OOM kill under concurrent load
        acquired = inference_semaphore.acquire(timeout=12000000)
        if not acquired:
            raise HTTPException(
                status_code=503,
                detail="Server busy — another inference is running. Please retry."
            )
        # Retrieve cached models (GPU-aware, loaded once at startup)
        rcnn_model, yolo_model, device = get_models()

        try:
            result = run_hybrid_pipeline_cached(
                input_path, output_path,
                rcnn_model=rcnn_model,
                yolo_model=yolo_model,
                device=device,
                conf=0.1,
            )
        finally:
            inference_semaphore.release()

        image_base64 = encode_image_b64(output_path)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(input_path):
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)

    record = save_to_db(
        db, "Mask R-CNN + YOLO (Hybrid)",
        file.filename, result["pipe_count"], 0.1
    )

    return {
        "model": "Mask R-CNN + YOLO (Hybrid)",
        "pipe_count": result["pipe_count"],
        "segments": result["segments"],
        "detection_id": record.id,
        "image_base64": image_base64
    }


# ── Single pipe endpoint (Mask R-CNN only, no YOLO stage) ────────────────────
@router.post("/single")
def detect_single_pipe(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Lightweight endpoint for images containing individual (non-stacked) pipes.
    Uses only Mask R-CNN — no YOLO second stage — so it is significantly
    faster than /detect/pipe_counts for single-pipe scenes.
    Returns pipe_count and an annotated image.
    """
    suffix = os.path.splitext(file.filename)[-1] or ".jpg"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
        shutil.copyfileobj(file.file, tmp_in)
        input_path = tmp_in.name

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_out:
        output_path = tmp_out.name

    try:
        acquired = inference_semaphore.acquire(timeout=12000000)
        if not acquired:
            raise HTTPException(
                status_code=503,
                detail="Server busy — another inference is running. Please retry."
            )
        # Reuse the same cached Mask R-CNN — no double loading
        rcnn_model, _, device = get_models()

        try:
            result = run_single_pipes_pipeline_cached(
                input_path, output_path,
                rcnn_model=rcnn_model,
                device=device,
                threshold=0.1,
            )
        finally:
            inference_semaphore.release()

        image_base64 = encode_image_b64(output_path)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(input_path):
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)

    record = save_to_db(
        db, "Mask R-CNN (Single Pipe)",
        file.filename, result["pipe_count"], 0.1
    )

    return {
        "model": "Mask R-CNN (Single Pipe)",
        "pipe_count": result["pipe_count"],
        "detection_id": record.id,
        "image_base64": image_base64
    }

# ── Fetch result by ID ────────────────────────────────────────────────────────
@router.get("/result/{detection_id}")
def get_result_image(detection_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import Response
    record = db.query(DetectionResult).filter(DetectionResult.id == detection_id).first()
    if not record or not record.output_image_base64:
        raise HTTPException(status_code=404, detail="Result not found")
    image_bytes = base64.b64decode(record.output_image_base64)
    return Response(content=image_bytes, media_type="image/jpeg")


@router.delete("/clear_data")
def clear_data(db: Session = Depends(get_db)):
    db.query(DetectionResult).delete()
    db.commit()
    return {"message": "Data cleared successfully"}