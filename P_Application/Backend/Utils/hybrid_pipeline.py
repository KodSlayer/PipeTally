"""
hybrid_pipeline.py
──────────────────
Hybrid two-stage pipe counting pipeline:

  Stage 1 — Mask R-CNN  (maskrcnn_pipeV2.pth)
    • Preprocess full image  (bilateral → CLAHE → unsharp)
    • Segment every pipe bundle / group  →  N binary masks
    • Crop each segment with ellipse masking  (from pipe1.py)

  Stage 2 — YOLO  (crop_yolo.pt)
    • Run crop_yolo.pt on every cropped segment  IN PARALLEL
    • Count the number of valid segmentation masks per crop
    • That count = number of inner pipes in that segment

  Output
    • Full annotated image:
        – Each segment filled with a distinct colour
        – White contour border around each segment
        – Per-segment YOLO count centred on that segment
        – Grand total header  "Segments: X  |  Total Pipes: Y"
    • Console summary
    • Saved to disk (optional)

Usage:
    python hybrid_pipeline.py                          # file-picker opens
    python hybrid_pipeline.py --image pipes63.jpg     # direct path
    python hybrid_pipeline.py --image pipes63.jpg --save output.jpg

Options:
    --image         Input image path  (dialog opens if omitted)
    --rcnn_model    Mask R-CNN .pth file   (default: maskrcnn_pipeV2.pth)
    --yolo_model    YOLO .pt  file         (default: crop_yolo.pt)
    --conf          MaskRCNN confidence    (default: 0.1)
    --mask_thresh   Mask binarisation      (default: 0.5)
    --min_area      Min mask px area       (default: 300)
    --iou_thresh    Containment filter     (default: 0.3)
    --yolo_conf     YOLO confidence        (default: 0.5)
    --yolo_imgsz    YOLO inference size    (default: 512)
    --yolo_min_area Min YOLO mask area     (default: 300)
    --workers       Parallel YOLO workers  (default: 4)
    --save          Output image path      (optional)
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import numpy as np
import torch
import torchvision
import torchvision.models.detection.faster_rcnn as faster_rcnn_mod
import torchvision.models.detection.mask_rcnn   as mask_rcnn_mod
import matplotlib.pyplot as plt
from ultralytics import YOLO


# ══════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════
def parse_args():
    p = argparse.ArgumentParser(description="Hybrid Mask R-CNN + YOLO pipe counting pipeline")
    p.add_argument("--image",        default=None,                  help="Input image path")
    p.add_argument("--rcnn_model",   default="maskrcnn_pipeV2.pth", help="Mask R-CNN .pth model")
    p.add_argument("--yolo_model",   default="crop_yolo26.pt",        help="YOLO .pt model")
    p.add_argument("--conf",         type=float, default=0.5,       help="MaskRCNN confidence threshold")
    p.add_argument("--mask_thresh",  type=float, default=0.5,       help="Mask binarisation threshold")
    p.add_argument("--min_area",     type=int,   default=300,       help="Min MaskRCNN mask area (px)")
    p.add_argument("--iou_thresh",   type=float, default=0.3,       help="Containment ratio to suppress inner masks")
    p.add_argument("--yolo_conf",    type=float, default=0.5,       help="YOLO detection confidence")
    p.add_argument("--yolo_imgsz",   type=int,   default=512,       help="YOLO inference image size")
    p.add_argument("--yolo_min_area",type=int,   default=300,       help="Min YOLO mask area (px)")
    p.add_argument("--workers",      type=int,   default=4,         help="Parallel YOLO crop workers")
    p.add_argument("--save",         default=None,                  help="Path to save annotated output image")
    return p.parse_args()


def pick_image_dialog() -> str:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="Select a pipe image",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff"), ("All", "*.*")],
    )
    root.destroy()
    return path


# ══════════════════════════════════════════════════════════════
#  STAGE 0 — PREPROCESSING
# ══════════════════════════════════════════════════════════════
def preprocess_image(img_rgb: np.ndarray) -> np.ndarray:
    """
    Bilateral denoising  →  CLAHE adaptive contrast  →  Unsharp masking.
    Input / output: RGB uint8 numpy array.
    """
    # 1. Edge-preserving noise removal
    img = cv2.bilateralFilter(img_rgb, d=5, sigmaColor=30, sigmaSpace=30)

    # 2. CLAHE on L channel (boosts dim pipe visibility)
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)

    # 3. Unsharp masking — crisp pipe boundaries
    blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=2)
    img = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)

    return img


# ══════════════════════════════════════════════════════════════
#  STAGE 1 — MASK R-CNN SEGMENTATION
# ══════════════════════════════════════════════════════════════
def load_maskrcnn(pth_path: str, device: torch.device):
    """Load a custom-trained Mask R-CNN (2-class) from a .pth state dict."""
    model = torchvision.models.detection.maskrcnn_resnet50_fpn(
        weights=None, box_detections_per_img=1000
    )
    in_feat = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = faster_rcnn_mod.FastRCNNPredictor(in_feat, 2)
    in_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    model.roi_heads.mask_predictor = mask_rcnn_mod.MaskRCNNPredictor(in_mask, 256, 2)
    model.load_state_dict(torch.load(pth_path, map_location=device))
    model.to(device).eval()
    print("✅  Mask R-CNN loaded")
    return model


def _filter_inner_masks(masks: list, iou_threshold: float = 0.3) -> list:
    """Drop masks that are mostly contained inside a larger mask.

    Optimized approach — per-pivot vectorised uint8 broadcasting:
    ─────────────────────────────────────────────────────────────
    • Areas pre-computed once  (original code recomputed masks[j].sum()
      inside the inner loop — O(N²) redundant work).
    • For each pivot i, the still-alive j > i masks are stacked into a
      compact (K, H, W) uint8 array and ALL intersections computed in
      one broadcasting call:  (stack & mask_i).sum(axis=(1,2))
    • Keeps uint8 throughout — 4× less memory and faster ops than float32.
    • The alive set shrinks as masks are suppressed, so later pivots do
      progressively less work (greedy ordering advantage preserved).
    """
    if not masks:
        return []

    n = len(masks)
    masks_sorted = sorted(masks, key=lambda m: m.sum(), reverse=True)

    if n == 1:
        return masks_sorted

    # Pre-compute areas once — avoids O(N²) redundant .sum() calls
    areas = np.array([m.sum() for m in masks_sorted], dtype=np.float32)

    keep = np.ones(n, dtype=bool)

    for i in range(n):
        if not keep[i]:
            continue

        mask_i = masks_sorted[i]  # (H, W) uint8

        # Indices of masks still alive and after position i
        alive_j = np.where(keep)[0]
        alive_j = alive_j[alive_j > i]

        if len(alive_j) == 0:
            continue

        # Stack only alive masks → compact (K, H, W) uint8
        stack = np.stack([masks_sorted[j] for j in alive_j])  # (K, H, W)

        # Vectorised intersection: broadcast mask_i over K slices, sum H×W
        intersections = (stack & mask_i[np.newaxis]).sum(axis=(1, 2)).astype(np.float32)
        containments  = intersections / (areas[alive_j] + 1e-6)

        # Suppress all alive_j where mask is largely inside pivot i
        suppress       = alive_j[containments > iou_threshold]
        keep[suppress] = False

    return [m for i, m in enumerate(masks_sorted) if keep[i]]



def run_maskrcnn(model, img_rgb: np.ndarray, device,
                 conf: float, mask_thresh: float,
                 min_area: int, iou_thresh: float) -> list:
    """
    Run Mask R-CNN on a preprocessed RGB image.
    Returns a list of filtered binary masks (H×W uint8).

    GPU memory safeguards
    ─────────────────────
    • Image must already be size-capped by the caller (run_hybrid_pipeline_cached
      caps at 1334 px before preprocessing). This keeps output mask memory at
      750 × 1334 × 1000 × float32 ≈ 4 GB — safe on a 14 GB GPU.
    • GPU tensor is explicitly deleted + empty_cache() called after inference.
    • CUDA OOM is caught and the inference is auto-retried on CPU.
    """
    tensor = torch.as_tensor(img_rgb / 255.0, dtype=torch.float32).permute(2, 0, 1)

    # ── Forward pass with OOM fallback ───────────────────────────────────────
    try:
        with torch.no_grad():
            out = model([tensor.to(device)])[0]
    except RuntimeError as exc:
        if "out of memory" in str(exc).lower() and str(device) != "cpu":
            print(f"⚠️  CUDA OOM — retrying on CPU (img {img_rgb.shape})")
            torch.cuda.empty_cache()
            with torch.no_grad():
                out = model([tensor.to("cpu")])[0]
        else:
            raise
    finally:
        # Always free the GPU input tensor immediately after forward pass
        del tensor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    keep = out["scores"] >= conf
    raw  = out["masks"][keep].cpu().numpy()

    valid = []
    for m in raw:
        mb = (m[0] > mask_thresh).astype(np.uint8)
        if mb.sum() >= min_area:
            valid.append(mb)

    print(f"📦  Detections before filtering : {len(valid)}")
    filtered = _filter_inner_masks(valid, iou_thresh)
    print(f"✂️   Detections after  filtering : {len(filtered)}")
    return filtered


# ══════════════════════════════════════════════════════════════
#  CROP UTILITY  (from pipe1.py — unchanged)
# ══════════════════════════════════════════════════════════════
def crop_single_pipe_circular(image: np.ndarray,
                               mask_bin: np.ndarray,
                               padding: int = 5) -> np.ndarray:
    """
    Crop the bounding-box of mask_bin from image, then black-out
    everything outside the fitted ellipse.
    Returns a BGR uint8 crop.
    """
    rows = np.any(mask_bin, axis=1)
    cols = np.any(mask_bin, axis=0)
    y_min, y_max = np.where(rows)[0][[0, -1]]
    x_min, x_max = np.where(cols)[0][[0, -1]]

    h, w = image.shape[:2]
    y1 = max(0, y_min - padding)
    y2 = min(h, y_max + padding + 1)
    x1 = max(0, x_min - padding)
    x2 = min(w, x_max + padding + 1)

    crop      = image[y1:y2, x1:x2].copy()
    mask_crop = mask_bin[y1:y2, x1:x2].copy()
    crop_h, crop_w = crop.shape[:2]

    contours, _ = cv2.findContours(
        mask_crop.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_NONE,
    )
    if not contours:
        return cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)

    largest = max(contours, key=cv2.contourArea)
    ellipse_mask = np.zeros((crop_h, crop_w), dtype=np.uint8)

    if len(largest) >= 5:
        ellipse = cv2.fitEllipse(largest)
        (cx, cy), (ma, mi), angle = ellipse
        expanded = ((cx, cy), (ma + padding, mi + padding), angle)
        cv2.ellipse(ellipse_mask, expanded, 255, -1)
    else:
        (cx, cy), radius = cv2.minEnclosingCircle(largest)
        cv2.circle(ellipse_mask, (int(cx), int(cy)),
                   int(radius) + padding, 255, -1)

    crop[ellipse_mask == 0] = [0, 0, 0]
    return cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)


# ══════════════════════════════════════════════════════════════
#  STAGE 2 — YOLO INNER COUNT  (parallel per-crop)
# ══════════════════════════════════════════════════════════════
def _count_inner_pipes_yolo(yolo_model, crop_bgr: np.ndarray,
                             conf: float, imgsz: int,
                             min_area: int,
                             device: torch.device | None = None) -> int:
    """
    Run crop_yolo.pt on a single BGR crop.
    Returns the number of valid segmentation masks found.
    Passes *device* to YOLO so GPU is used when available.
    """
    # YOLO expects RGB
    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    ch, cw = crop_rgb.shape[:2]

    # Resolve device string for YOLO (e.g. "cuda:0" or "cpu")
    yolo_device = None
    if device is not None:
        yolo_device = "cuda:0" if device.type == "cuda" else "cpu"

    results = yolo_model(
        crop_rgb,
        conf=conf,
        imgsz=imgsz,
        retina_masks=True,
        verbose=False,
        device=yolo_device,
    )[0]

    if results.masks is None:
        return 1   # Mask R-CNN confirmed a segment → at least 1 pipe

    raw_masks = results.masks.data.cpu().numpy()   # (N, H, W) — .cpu() handles GPU tensors
    count = 0
    for mask in raw_masks:
        m = cv2.resize(mask, (cw, ch), interpolation=cv2.INTER_LINEAR)
        if (m > 0.4).sum() >= min_area:
            count += 1

    # Always return at least 1 — Mask R-CNN already confirmed this segment exists
    return max(1, count)


def count_all_crops_parallel(yolo_model, crops: list,
                              conf: float, imgsz: int,
                              min_area: int, num_workers: int,
                              device: torch.device | None = None) -> list:
    """
    Count inner pipes for every crop in *crops* using a ThreadPoolExecutor.
    Returns a list of counts in the same order as *crops*.

    NOTE: YOLO's forward pass is NOT thread-safe on a single model instance.
          We serialise the actual inference with a lock so threads only
          parallelise the lightweight bookkeeping / CPU work around it.
          On GPU the lock also prevents simultaneous CUDA stream contention.
    """
    import threading
    _lock = threading.Lock()

    def _worker(idx_crop):
        idx, crop_bgr = idx_crop
        with _lock:
            count = _count_inner_pipes_yolo(
                yolo_model, crop_bgr, conf, imgsz, min_area, device=device
            )
        return idx, count

    counts = [0] * len(crops)
    with ThreadPoolExecutor(max_workers=num_workers) as pool:
        futures = {pool.submit(_worker, (i, c)): i for i, c in enumerate(crops)}
        for future in as_completed(futures):
            idx, cnt = future.result()
            counts[idx] = cnt

    return counts


# ══════════════════════════════════════════════════════════════
#  FINAL VISUALISATION
# ══════════════════════════════════════════════════════════════
def build_annotated_image(orig_rgb: np.ndarray,
                           masks: list,
                           inner_counts: list,
                           min_area: int = 300):
    """
    Produce the final annotated RGB image:
      • Each segment → distinct colour fill
      • White contour border
      • YOLO inner-pipe count centred on that segment
      • Header: "Segments: X  |  Total Pipes: Y"

    Returns (annotated_rgb, total_segments, total_pipes).
    """
    image   = orig_rgb.copy()
    overlay = np.zeros_like(image, dtype=np.uint8)

    np.random.seed(42)
    colors = [
        tuple(int(c) for c in col)
        for col in np.random.randint(50, 230, size=(len(masks), 3))
    ]

    # ── Build colour overlay ──────────────────────────────────
    valid = []
    for i, (mask_bin, cnt) in enumerate(zip(masks, inner_counts)):
        if mask_bin.sum() < min_area:
            continue
        overlay[mask_bin == 1] = colors[i]
        valid.append((mask_bin, cnt, colors[i]))

    # Blend
    result = cv2.addWeighted(image, 0.45, overlay, 0.55, 0)

    # ── Contours + per-segment label ─────────────────────────
    for mask_bin, cnt, color in valid:
        # White border
        contours, _ = cv2.findContours(
            mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(result, contours, -1, (255, 255, 255), 1)

        # Count label centred on mask centroid
        ys, xs = np.where(mask_bin)
        cx, cy = int(np.mean(xs)), int(np.mean(ys))
        label  = str(cnt)
        font, scale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2
        (tw, th), _ = cv2.getTextSize(label, font, scale, thick)
        cv2.rectangle(
            result,
            (cx - tw // 2 - 3, cy - th - 5),
            (cx + tw // 2 + 3, cy + 5),
            (0, 0, 0), -1
        )
        cv2.putText(
            result, label,
            (cx - tw // 2, cy),
            font, scale, (255, 255, 0), thick
        )

    # ── Grand total header ────────────────────────────────────
    total_segs  = len(valid)
    total_pipes = sum(cnt for _, cnt, _ in valid)
    # header = f"Segments: {total_segs}  |  Total Pipes: {total_pipes}"
    # font, scale, thick = cv2.FONT_HERSHEY_SIMPLEX, 1.1, 3
    # (hw, hh), _ = cv2.getTextSize(header, font, scale, thick)
    # cv2.rectangle(result, (8, 8), (hw + 18, hh + 22), (0, 0, 0), -1)
    # cv2.putText(result, header, (13, hh + 14), font, scale, (0, 255, 0), thick)

    return result, total_segs, total_pipes


# ══════════════════════════════════════════════════════════════
#  PUBLIC API  (for use from FastAPI / other scripts)
# ══════════════════════════════════════════════════════════════

def run_hybrid_pipeline_cached(
    input_path: str,
    output_path: str | None,
    rcnn_model,
    yolo_model,
    device: torch.device,
    conf: float        = 0.1,
    mask_thresh: float = 0.5,
    min_area: int      = 300,
    iou_thresh: float  = 0.3,
    yolo_conf: float   = 0.5,
    yolo_imgsz: int    = 512,
    yolo_min_area: int = 300,
    num_workers: int   = 4,
) -> dict:
    """
    FastAPI entry point — accepts *pre-loaded* model objects.

    Unlike run_hybrid_pipeline(), this function never touches disk for
    model weights.  Both models are loaded once at server startup via
    model_cache.warm_up() and passed in here, eliminating the 15-40 s
    cold-start penalty on every request.

    GPU support: pass device=torch.device("cuda") and both Mask R-CNN
    tensors and YOLO inference will run on the GPU automatically.

    Returns dict: {"segments": N, "pipe_count": M}
    """
    # ── Load image ────────────────────────────────────────────
    bgr = cv2.imread(input_path)
    if bgr is None:
        raise ValueError(f"Could not read image: {input_path}")
    orig_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # ── Cap image size BEFORE anything else ───────────────────
    # Mask R-CNN's internals downscale to max ~1333 px anyway, so capping
    # here ensures masks, crops, and annotation all share the same resolution.
    # Without this, run_maskrcnn was resizing internally → masks at 1334 px
    # but the image still full-res → boolean index shape mismatch.
    MAX_SIDE = 1334
    h0, w0   = orig_rgb.shape[:2]
    if max(h0, w0) > MAX_SIDE:
        scale    = MAX_SIDE / max(h0, w0)
        orig_rgb = cv2.resize(
            orig_rgb, (int(w0 * scale), int(h0 * scale)),
            interpolation=cv2.INTER_AREA
        )

    # ── Preprocess ────────────────────────────────────────────
    prep_rgb = preprocess_image(orig_rgb)

    # ── Stage 1: Mask R-CNN (cached model, GPU-aware) ─────────
    masks = run_maskrcnn(rcnn_model, prep_rgb, device,
                         conf, mask_thresh, min_area, iou_thresh)

    # ── Crop each valid segment ───────────────────────────────
    valid_masks = [m for m in masks if m.sum() >= min_area]
    crops = [
        crop_single_pipe_circular(prep_rgb, m, padding=5)
        for m in valid_masks
    ]

    # ── Stage 2: YOLO inner count (cached model, GPU-aware) ───
    inner_counts = count_all_crops_parallel(
        yolo_model, crops, yolo_conf, yolo_imgsz, yolo_min_area,
        num_workers, device=device
    )

    # ── Build output image ────────────────────────────────────
    annotated, total_segs, total_pipes = build_annotated_image(
        orig_rgb, valid_masks, inner_counts, min_area
    )

    if output_path:
        cv2.imwrite(output_path, cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR))

    return {"segments": total_segs, "pipe_count": total_pipes}


def run_hybrid_pipeline(
    input_path: str,
    output_path: str | None = None,
    rcnn_model_path: str  = "maskrcnn_pipeV4.pth",
    yolo_model_path: str  = "crop_yolo26.pt",
    conf: float           = 0.1,
    mask_thresh: float    = 0.5,
    min_area: int         = 300,
    iou_thresh: float     = 0.3,
    yolo_conf: float      = 0.5,
    yolo_imgsz: int       = 512,
    yolo_min_area: int    = 300,
    num_workers: int      = 4,
):
    """
    Standalone / CLI entry point — loads models from file paths each call.
    Use run_hybrid_pipeline_cached() for the FastAPI path.
    Returns dict: {"segments": N, "pipe_count": M}
    """
    # ── Load image ────────────────────────────────────────────
    bgr = cv2.imread(input_path)
    if bgr is None:
        raise ValueError(f"Could not read image: {input_path}")
    orig_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # ── Preprocess ────────────────────────────────────────────
    prep_rgb = preprocess_image(orig_rgb)

    # ── Stage 1: Mask R-CNN ───────────────────────────────────
    device      = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rcnn_model  = load_maskrcnn(rcnn_model_path, device)
    masks       = run_maskrcnn(rcnn_model, prep_rgb, device,
                               conf, mask_thresh, min_area, iou_thresh)

    # ── Crop each segment ─────────────────────────────────────
    crops = [
        crop_single_pipe_circular(prep_rgb, m, padding=5)
        for m in masks
        if m.sum() >= min_area
    ]
    valid_masks = [m for m in masks if m.sum() >= min_area]

    # ── Stage 2: YOLO inner count (parallel) ─────────────────
    yolo_model   = YOLO(yolo_model_path)
    inner_counts = count_all_crops_parallel(
        yolo_model, crops, yolo_conf, yolo_imgsz, yolo_min_area,
        num_workers, device=device
    )

    # ── Build output image ────────────────────────────────────
    annotated, total_segs, total_pipes = build_annotated_image(
        orig_rgb, valid_masks, inner_counts, min_area
    )

    if output_path:
        cv2.imwrite(output_path, cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR))

    return {"segments": total_segs, "pipe_count": total_pipes}


# ══════════════════════════════════════════════════════════════
#  MAIN  (interactive / CLI use)
# ══════════════════════════════════════════════════════════════
def main():
    args = parse_args()

    # ── Image selection ───────────────────────────────────────
    if not args.image:
        print("📂  No --image provided — opening file picker …")
        args.image = pick_image_dialog()
        if not args.image:
            sys.exit("❌  No image selected.")

    if not os.path.isfile(args.image):
        sys.exit(f"❌  Image not found: {args.image}")
    if not os.path.isfile(args.rcnn_model):
        sys.exit(f"❌  Mask R-CNN model not found: {args.rcnn_model}")
    if not os.path.isfile(args.yolo_model):
        sys.exit(f"❌  YOLO model not found: {args.yolo_model}")

    # ── Load image ────────────────────────────────────────────
    bgr = cv2.imread(args.image)
    if bgr is None:
        sys.exit(f"❌  Could not read image: {args.image}")
    orig_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = orig_rgb.shape[:2]
    print(f"📷  Image : {args.image}  ({w}×{h})")

    # ── Preprocess ────────────────────────────────────────────
    print("🔧  Preprocessing (bilateral → CLAHE → unsharp) …")
    prep_rgb = preprocess_image(orig_rgb)

    # ════════════════════════════════════════════════════════
    #  STAGE 1 — Mask R-CNN: segment pipe groups
    # ════════════════════════════════════════════════════════
    device     = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"⚡  Device : {device}")
    rcnn_model = load_maskrcnn(args.rcnn_model, device)
    print(f"🔍  Running Mask R-CNN (conf={args.conf}) …")
    masks      = run_maskrcnn(
        rcnn_model, prep_rgb, device,
        args.conf, args.mask_thresh, args.min_area, args.iou_thresh
    )
    print(f"📦  Final segments : {len(masks)}")

    # ── Crop each valid segment ───────────────────────────────
    valid_masks = [m for m in masks if m.sum() >= args.min_area]
    print(f"✂️   Cropping {len(valid_masks)} segment(s) …")
    crops = [
        crop_single_pipe_circular(prep_rgb, m, padding=5)
        for m in valid_masks
    ]

    # ════════════════════════════════════════════════════════
    #  STAGE 2 — YOLO: count inner pipes per crop (parallel)
    # ════════════════════════════════════════════════════════
    print(f"🤖  Loading YOLO model: {args.yolo_model}")
    yolo_model = YOLO(args.yolo_model)
    print(f"🔢  Counting inner pipes in {len(crops)} crop(s)"
          f" using {args.workers} worker(s) …")

    inner_counts = count_all_crops_parallel(
        yolo_model, crops,
        args.yolo_conf, args.yolo_imgsz, args.yolo_min_area,
        args.workers,
    )

    for i, cnt in enumerate(inner_counts):
        print(f"   Segment {i+1:>4}: {cnt} pipe(s)")

    # ════════════════════════════════════════════════════════
    #  Build final annotated image
    # ════════════════════════════════════════════════════════
    annotated, total_segs, total_pipes = build_annotated_image(
        orig_rgb, valid_masks, inner_counts, args.min_area
    )

    sep = "─" * 55
    print(f"\n{sep}")
    print(f"  Pipe segments detected : {total_segs}")
    print(f"  Total inner pipes      : {total_pipes}  (YOLO sum across all segments)")
    print(f"{sep}")

    # ── Save (optional) ───────────────────────────────────────
    if args.save:
        out_bgr = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)
        cv2.imwrite(args.save, out_bgr)
        print(f"💾  Saved annotated image to: {args.save}")

    # ── Display ───────────────────────────────────────────────
    plt.figure(figsize=(16, 10))
    plt.imshow(annotated)
    plt.axis("off")
    # plt.title(
    #     f"Segments: {total_segs}  |  Total Pipes: {total_pipes}",
    #     fontsize=14, fontweight="bold"
    # )
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
