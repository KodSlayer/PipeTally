"""
model_cache.py
──────────────
Singleton cache for Mask R-CNN and YOLO models.

Both models are loaded ONCE at server startup and reused for every
subsequent request, eliminating the per-request cold-start cost.

GPU memory notes
────────────────
Mask R-CNN outputs one segmentation mask per detection, at the original
image resolution.  With box_detections_per_img=1000 and a 3000×2000 image:
  1000 × 3000 × 2000 × float32 ≈ 24 GB  → instant OOM on any GPU.
We cap detections at 300 (more than enough for pipe bundles) and set
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to reduce fragmentation.
"""

import os
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import os
import threading

import torch
import torchvision
import torchvision.models.detection.faster_rcnn as faster_rcnn_mod
import torchvision.models.detection.mask_rcnn   as mask_rcnn_mod
from ultralytics import YOLO

# ── Resolved paths (relative to this file → Utils/) ──────────────────────────
_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
_RCNN_PATH = os.path.join(_UTILS_DIR, "maskrcnn_pipeV4.pth")
_YOLO_PATH = os.path.join(_UTILS_DIR, "crop_yolo26.pt")

# ── Shared state ──────────────────────────────────────────────────────────────
_rcnn_model = None
_yolo_model = None
_device     = None
_load_lock  = threading.Lock()          # guards one-time model loading

# Only 1 inference at a time — prevents OOM under concurrent API load
inference_semaphore = threading.Semaphore(1)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _resolve_device() -> torch.device:
    """Pick CUDA if available, else CPU. Logs the result once."""
    if torch.cuda.is_available():
        dev = torch.device("cuda")
        gpu_name = torch.cuda.get_device_name(0)
        total_mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        print(f"⚡  GPU detected : {gpu_name}  ({total_mem:.1f} GB VRAM)")
    else:
        dev = torch.device("cpu")
        print("⚡  No GPU found — running on CPU")
    return dev


def _load_maskrcnn(device: torch.device):
    """Load custom-trained Mask R-CNN from the .pth file onto *device*."""
    print(f"🔄  Loading Mask R-CNN from: {_RCNN_PATH}")
    m = torchvision.models.detection.maskrcnn_resnet50_fpn(
        weights=None,
        # 750 detections: handles images with 600+ pipes (with margin).
        # Output masks are at input-image resolution; keeping MAX_SIDE=1334
        # in inference functions limits each mask to ~1334×1000 px max,
        # so 750 masks × 1334×1000 × float32 ≈ 4 GB — safe on a 14 GB GPU.
        box_detections_per_img=750
    )
    in_feat = m.roi_heads.box_predictor.cls_score.in_features
    m.roi_heads.box_predictor = faster_rcnn_mod.FastRCNNPredictor(in_feat, 2)
    in_mask = m.roi_heads.mask_predictor.conv5_mask.in_channels
    m.roi_heads.mask_predictor = mask_rcnn_mod.MaskRCNNPredictor(in_mask, 256, 2)

    m.load_state_dict(
        torch.load(_RCNN_PATH, map_location=device, weights_only=False)
    )
    m.to(device).eval()

    if device.type == "cuda":
        # Warm the CUDA kernels with a tiny dummy forward pass
        with torch.no_grad():
            dummy = torch.zeros(1, 3, 64, 64, device=device)
            try:
                m([dummy])
            except Exception:
                pass
        # Release any fragmented memory left by the warm-up
        torch.cuda.empty_cache()
    print("✅  Mask R-CNN loaded and cached.")
    return m


def _load_yolo(device: torch.device):
    """Load YOLO from the .pt file and move it to *device*."""
    print(f"🔄  Loading YOLO from: {_YOLO_PATH}")
    m = YOLO(_YOLO_PATH)
    if device.type == "cuda":
        m.to("cuda")
        print(f"   YOLO moved to GPU ({torch.cuda.get_device_name(0)})")
    else:
        print("   YOLO running on CPU")
    print("✅  YOLO loaded and cached.")
    return m


# ── Public API ────────────────────────────────────────────────────────────────

def get_models():
    """
    Return the shared (rcnn_model, yolo_model, device) tuple.

    • Loads both models on first call (double-checked locking, thread-safe).
    • Returns the cached instances on every subsequent call — zero I/O.
    """
    global _rcnn_model, _yolo_model, _device

    # Fast path — already loaded
    if _rcnn_model is not None and _yolo_model is not None:
        return _rcnn_model, _yolo_model, _device

    with _load_lock:
        # Re-check inside the lock (another thread may have loaded first)
        if _rcnn_model is None or _yolo_model is None:
            _device     = _resolve_device()
            _rcnn_model = _load_maskrcnn(_device)
            _yolo_model = _load_yolo(_device)

    return _rcnn_model, _yolo_model, _device


def warm_up():
    """
    Pre-load both models at server startup.
    Call this from the FastAPI lifespan / startup event so the first
    real request pays only inference cost, not model-loading cost.
    """
    print("🚀  Warming up models …")
    get_models()
    print("🟢  Both models are warm and ready to serve requests.")
