import os
import csv
import json
import time
import torch
import torchvision
import cv2
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Load Model
# -----------------------------
def load_model(pth_path, device):
    model = torchvision.models.detection.maskrcnn_resnet50_fpn(weights=None, box_detections_per_img=1000)
    num_classes = 2

    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = torchvision.models.detection.faster_rcnn.FastRCNNPredictor(
        in_features, num_classes
    )
    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    model.roi_heads.mask_predictor = torchvision.models.detection.mask_rcnn.MaskRCNNPredictor(
        in_features_mask, 256, num_classes
    )

    model.load_state_dict(torch.load(pth_path, map_location=device, weights_only=False))
    model.to(device)
    model.eval()
    print("✅ Model loaded!")
    return model


# -----------------------------
# Preprocess
# -----------------------------
def preprocess(image_path, max_side: int = 1334):
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # ── Cap image size before GPU inference ───────────────────────────────────
    # Mask R-CNN's internal transform downscales to ~1333 px anyway;
    # capping here prevents creating a huge input tensor on the GPU.
    h, w = img.shape[:2]
    if max(h, w) > max_side:
        scale = max_side / max(h, w)
        img   = cv2.resize(img, (int(w * scale), int(h * scale)),
                           interpolation=cv2.INTER_AREA)

    # ── Step 1: Bilateral denoising ───────────────────────────────────────
    img = cv2.bilateralFilter(img, d=5, sigmaColor=30, sigmaSpace=30)

    # ── Step 2: CLAHE on L channel (adaptive contrast) ────────────────────
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)

    # ── Step 3: Unsharp masking (edge sharpening) ─────────────────────────
    blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=2)
    img = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)

    img_tensor = torch.as_tensor(img / 255.0, dtype=torch.float32).permute(2, 0, 1)
    return img_tensor, img


# -----------------------------
# Inference
# -----------------------------
def predict(model, img_tensor, device, threshold=0.5):
    """Run inference with OOM fallback and immediate GPU memory release."""
    try:
        with torch.no_grad():
            outputs = model([img_tensor.to(device)])
    except RuntimeError as exc:
        if "out of memory" in str(exc).lower() and str(device) != "cpu":
            print(f"⚠️  CUDA OOM in single-pipe predict — retrying on CPU")
            torch.cuda.empty_cache()
            with torch.no_grad():
                outputs = model([img_tensor.to("cpu")])
        else:
            raise
    finally:
        del img_tensor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    pred = outputs[0]
    keep = pred["scores"] >= threshold
    return {
        "boxes":  pred["boxes"][keep].cpu().numpy(),
        "scores": pred["scores"][keep].cpu().numpy(),
        "masks":  pred["masks"][keep].cpu().numpy(),
    }


# -----------------------------
# Visualize — Solid masks only, count on top
# -----------------------------
def visualize_masks(original_img, preds, mask_thresh=0.5, min_area=300):
    image = original_img.copy()
    overlay = np.zeros_like(image, dtype=np.uint8)

    masks  = preds["masks"]
    count  = 0

    # Generate distinct colors for each pipe
    np.random.seed(42)
    colors = [
        tuple(int(c) for c in color)
        for color in np.random.randint(50, 255, size=(len(masks), 3))
    ]

    for i in range(len(masks)):
        mask_bin = (masks[i, 0] > mask_thresh).astype(np.uint8)

        # Skip tiny detections (noise)
        if mask_bin.sum() < min_area:
            continue

        count += 1
        color = colors[i]

        # Fill solid color on overlay for this pipe
        overlay[mask_bin == 1] = color

    # Blend overlay onto original image
    result = cv2.addWeighted(image, 0.45, overlay, 0.55, 0)

    # Draw contour borders between pipes for clear separation
    for i in range(len(masks)):
        mask_bin = (masks[i, 0] > mask_thresh).astype(np.uint8)
        if mask_bin.sum() < min_area:
            continue
        contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(result, contours, -1, (255, 255, 255), 1)  # white border



    # Show
    plt.figure(figsize=(16, 10))
    plt.imshow(result)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

    print(f"\n✅ Total pipes detected: {count}")
    return count


# -----------------------------
# Save annotated image to disk
# -----------------------------
def save_annotated_image(original_img, preds, out_path, mask_thresh=0.5, min_area=300):
    """Same as visualize_masks but saves to disk instead of displaying."""
    image   = original_img.copy()
    overlay = np.zeros_like(image, dtype=np.uint8)
    masks   = preds["masks"]
    count   = 0

    np.random.seed(42)
    colors = [
        tuple(int(c) for c in color)
        for color in np.random.randint(50, 255, size=(len(masks), 3))
    ]

    for i in range(len(masks)):
        mask_bin = (masks[i, 0] > mask_thresh).astype(np.uint8)
        if mask_bin.sum() < min_area:
            continue
        count += 1
        overlay[mask_bin == 1] = colors[i]

    result = cv2.addWeighted(image, 0.45, overlay, 0.55, 0)

    for i in range(len(masks)):
        mask_bin = (masks[i, 0] > mask_thresh).astype(np.uint8)
        if mask_bin.sum() < min_area:
            continue
        contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(result, contours, -1, (255, 255, 255), 1)



    cv2.imwrite(out_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    return count


# ── Cached entry point (FastAPI) — accepts pre-loaded model objects ───────────
def run_single_pipes_pipeline_cached(
    input_path: str,
    output_path: str,
    rcnn_model,
    device,
    threshold: float  = 0.1,
    mask_thresh: float = 0.5,
    min_area: int     = 300,
) -> dict:
    """
    FastAPI entry point — uses pre-loaded Mask R-CNN model from model_cache.
    No model loading from disk; just preprocess → infer → annotate → save.
    Returns dict: {"pipe_count": N}
    """
    img_tensor, orig_img = preprocess(input_path)
    preds = predict(rcnn_model, img_tensor, device, threshold)
    count = save_annotated_image(orig_img, preds, output_path, mask_thresh, min_area)
    return {"pipe_count": count}


# ── Standalone / CLI entry point — loads model from disk each call ────────────
def run_single_pipes_pipeline(input_path: str, output_path: str,
                              threshold=0.1, mask_thresh=0.5, min_area=300):
    """CLI / standalone use. Use run_single_pipes_pipeline_cached() from FastAPI."""
    from Utils.model_cache import get_models
    rcnn_model, _, device = get_models()   # reuse cached model if server is running
    img_tensor, orig_img = preprocess(input_path)
    preds = predict(rcnn_model, img_tensor, device, threshold)
    count = save_annotated_image(orig_img, preds, output_path, mask_thresh, min_area)
    return {"pipe_count": count}


# ── Local execution ──────────────────────────────────────
# if __name__ == "__main__":
#     PTH_PATH    = "maskrcnn_pipeV2.pth"
#     IMAGE_PATH  = "../../images/pipes18.jpg"
#     THRESHOLD   = 0.1
#     MASK_THRESH = 0.5
#     MIN_AREA    = 300

#     device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#     print(f"⚡ Using: {device}")

#     model = load_model(PTH_PATH, device)
#     img_tensor, orig_img = preprocess(IMAGE_PATH)
#     preds = predict(model, img_tensor, device, THRESHOLD)
#     visualize_masks(orig_img, preds, MASK_THRESH, MIN_AREA)
