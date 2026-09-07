from typing import Tuple, Optional
import os
import cv2
import numpy as np
from PIL import Image
from src.art_engine.art_config import NATURAL_OVERLAP_ERODE

# ---------------------------------------------------------------------------
# rembg & mediapipe import fallbacks
# ---------------------------------------------------------------------------
try:
    from rembg import remove as rembg_remove
    _REMBG_AVAILABLE = True
except ImportError:
    _REMBG_AVAILABLE = False

try:
    import mediapipe as mp
    _MEDIAPIPE_AVAILABLE = True
except ImportError:
    _MEDIAPIPE_AVAILABLE = False


def _extract_silhouette_rembg(color_np: np.ndarray) -> np.ndarray:
    """Derives binary person silhouette using rembg ML background removal."""
    pil_color = Image.fromarray(color_np)
    output_rgba = rembg_remove(pil_color)
    alpha = np.array(output_rgba)[:, :, 3]
    _, mask = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def _extract_silhouette_otsu(gray_np: np.ndarray) -> np.ndarray:
    """Fallback silhouette when rembg is unavailable."""
    h, w = gray_np.shape
    _, thresh = cv2.threshold(gray_np, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    mask = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    cv2.ellipse(mask, (w // 2, int(h * 0.38)), (int(w * 0.3), int(h * 0.35)), 0, 0, 360, 255, -1)
    shoulder_poly = np.array([
        [int(w * 0.2), int(h * 0.6)],
        [int(w * 0.8), int(h * 0.6)],
        [w, h], [0, h]
    ], dtype=np.int32)
    cv2.fillPoly(mask, [shoulder_poly], 255)
    return mask


def _detect_hair_heuristic(
    gray_np: np.ndarray,
    color_np: np.ndarray,
    face_rect: Tuple[int, int, int, int],
    silhouette_mask: np.ndarray
) -> np.ndarray:
    """
    Heuristic hair detection:
    Identifies hair in the region above and around the face bounding box by
    excluding skin-colored pixels within the head ROI.
    """
    h, w = gray_np.shape
    fx, fy, fw, fh = face_rect
    hair_mask = np.zeros((h, w), dtype=np.uint8)

    # Search region above and around face: 65% above forehead, 35% sideways
    top = max(0, fy - int(fh * 0.65))
    bottom = min(h, fy + int(fh * 0.85))
    left = max(0, fx - int(fw * 0.35))
    right = min(w, fx + fw + int(fw * 0.35))

    roi_color = color_np[top:bottom, left:right]
    roi_sil = silhouette_mask[top:bottom, left:right]

    if roi_color.size == 0:
        return hair_mask

    # Skin color thresholding (HSV + YCrCb)
    hsv = cv2.cvtColor(roi_color, cv2.COLOR_RGB2HSV)
    ycrcb = cv2.cvtColor(roi_color, cv2.COLOR_RGB2YCrCb)

    # Typical skin color ranges
    lower_hsv = np.array([0, 15, 60], dtype=np.uint8)
    upper_hsv = np.array([25, 170, 255], dtype=np.uint8)
    mask_hsv = cv2.inRange(hsv, lower_hsv, upper_hsv)

    lower_ycrcb = np.array([0, 133, 77], dtype=np.uint8)
    upper_ycrcb = np.array([255, 173, 127], dtype=np.uint8)
    mask_ycrcb = cv2.inRange(ycrcb, lower_ycrcb, upper_ycrcb)

    skin_roi = cv2.bitwise_and(mask_hsv, mask_ycrcb)

    # Non-skin pixels inside ROI silhouette represent hair
    hair_roi = cv2.bitwise_and(roi_sil, cv2.bitwise_not(skin_roi))

    hair_mask[top:bottom, left:right] = hair_roi
    return hair_mask


def extract_masks(
    gray_np: np.ndarray,
    color_np: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extracts three binary masks (255 = active, 0 = background):

    1. silhouette_mask — full person outline (head + neck + body).
    2. natural_mask    — UNION of face skin, hair, ears, and neck (rendered as pencil sketch).
    3. clothing_mask   — silhouette minus natural_mask (rendered as typographic word art).
    """
    h, w = gray_np.shape

    # ── Step 1: Silhouette ──────────────────────────────────────────────────
    if _REMBG_AVAILABLE:
        silhouette_mask = _extract_silhouette_rembg(color_np)
    else:
        silhouette_mask = _extract_silhouette_otsu(gray_np)

    silhouette_mask = cv2.GaussianBlur(silhouette_mask, (15, 15), 0)
    _, silhouette_mask = cv2.threshold(silhouette_mask, 100, 255, cv2.THRESH_BINARY)

    # ── Step 2: Face, Neck & Hair detection (Natural Mask) ───────────────────
    hsv = cv2.cvtColor(color_np, cv2.COLOR_RGB2HSV)
    ycrcb = cv2.cvtColor(color_np, cv2.COLOR_RGB2YCrCb)
    skin_ycrcb = cv2.inRange(ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127]))
    skin_hsv = cv2.inRange(hsv, np.array([0, 15, 55]), np.array([28, 175, 255]))
    skin = cv2.bitwise_and(skin_ycrcb, skin_hsv)
    skin = cv2.bitwise_and(skin, silhouette_mask)
    skin_close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    skin_filled = cv2.morphologyEx(skin, cv2.MORPH_CLOSE, skin_close_k)

    skin_px = np.count_nonzero(skin_filled)
    sil_px = max(1, np.count_nonzero(silhouette_mask))

    if skin_px >= sil_px * 0.05:
        # Reliable skin segmentation capturing face + natural neck down into collar
        skin_pts = np.argwhere(skin_filled > 0)
        min_y = skin_pts[:, 0].min()
        max_y = skin_pts[:, 0].max()
        min_x = skin_pts[:, 1].min()
        max_x = skin_pts[:, 1].max()
        center_x = (min_x + max_x) // 2
        span_w = max_x - min_x

        # Hair is above the eyes/forehead in the silhouette
        chin_y = int(min_y + (max_y - min_y) * 0.55)
        head_sil = silhouette_mask.copy()
        head_sil[chin_y:, :] = 0
        head_left = max(0, center_x - int(span_w * 0.95))
        head_right = min(w, center_x + int(span_w * 0.95))
        head_sil[:, :head_left] = 0
        head_sil[:, head_right:] = 0
        natural_mask = cv2.bitwise_or(skin_filled, head_sil)
    else:
        # Fallback: Face cascade or center ellipse
        face_mask = np.zeros((h, w), dtype=np.uint8)
        faces = []
        if hasattr(cv2, 'CascadeClassifier'):
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            faces = face_cascade.detectMultiScale(
                gray_np, scaleFactor=1.1, minNeighbors=3, minSize=(60, 60)
            )

        if len(faces) > 0:
            largest_face = max(faces, key=lambda r: r[2] * r[3])
            fx, fy, fw, fh = largest_face
            center_x = fx + fw // 2
            center_y = fy + int(fh * 0.45)
            axes_w = int(fw * 0.80)
            axes_h = int(fh * 1.05)
            cv2.ellipse(face_mask, (center_x, center_y), (axes_w, axes_h), 0, 0, 360, 255, -1)
            chin_y = min(h, fy + int(fh * 1.10))
            head_top_region = silhouette_mask.copy()
            head_top_region[chin_y:, :] = 0
            natural_mask = cv2.bitwise_or(face_mask, head_top_region)
        else:
            center_x = w // 2
            center_y = int(h * 0.30)
            cv2.ellipse(
                face_mask, (center_x, center_y),
                (int(w * 0.28), int(h * 0.35)), 0, 0, 360, 255, -1
            )
            natural_mask = face_mask

    # Morphological close/open to unify hair and skin into one contiguous region
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    natural_mask = cv2.morphologyEx(natural_mask, cv2.MORPH_CLOSE, close_kernel)
    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    natural_mask = cv2.morphologyEx(natural_mask, cv2.MORPH_OPEN, open_kernel)

    # Smooth edges of natural mask
    natural_mask = cv2.GaussianBlur(natural_mask, (21, 21), 0)
    _, natural_mask = cv2.threshold(natural_mask, 100, 255, cv2.THRESH_BINARY)

    # Clip natural_mask to silhouette
    natural_mask = cv2.bitwise_and(natural_mask, silhouette_mask)

    # ── Step 4: Clothing Mask ──────────────────────────────────────────────
    # Clothing is strictly silhouette minus natural_mask
    clothing_mask = cv2.bitwise_and(silhouette_mask, cv2.bitwise_not(natural_mask))

    return silhouette_mask, natural_mask, clothing_mask


def save_debug_masks(
    gray_np: np.ndarray,
    color_np: np.ndarray,
    output_dir: str = "./debug_output",
) -> None:
    """Debug utility to save silhouette_mask, natural_mask, clothing_mask PNGs."""
    os.makedirs(output_dir, exist_ok=True)
    silhouette_mask, natural_mask, clothing_mask = extract_masks(gray_np, color_np)

    cv2.imwrite(os.path.join(output_dir, "silhouette_mask.png"), silhouette_mask)
    cv2.imwrite(os.path.join(output_dir, "natural_mask.png"), natural_mask)
    cv2.imwrite(os.path.join(output_dir, "clothing_mask.png"), clothing_mask)
    cv2.imwrite(os.path.join(output_dir, "face_mask.png"), natural_mask)
    cv2.imwrite(os.path.join(output_dir, "body_mask.png"), clothing_mask)


    # Overview overlay: natural in blue, clothing in green
    overview = cv2.cvtColor(color_np, cv2.COLOR_RGB2BGR).copy()
    overview[natural_mask > 0] = (overview[natural_mask > 0] * 0.4 + np.array([200, 100, 50]) * 0.6).astype(np.uint8)
    overview[clothing_mask > 0] = (overview[clothing_mask > 0] * 0.4 + np.array([50, 200, 50]) * 0.6).astype(np.uint8)
    cv2.imwrite(os.path.join(output_dir, "mask_overview.png"), overview)

    print(f"[Debug] Masks saved to '{output_dir}':")
    print(f"  silhouette active pixels : {np.count_nonzero(silhouette_mask)}")
    print(f"  natural    active pixels : {np.count_nonzero(natural_mask)}")
    print(f"  clothing   active pixels : {np.count_nonzero(clothing_mask)}")


def extract_silhouette_mask(gray_np: np.ndarray, color_np: np.ndarray) -> np.ndarray:
    """Legacy helper returning full silhouette mask."""
    silhouette_mask, _, _ = extract_masks(gray_np, color_np)
    return silhouette_mask
