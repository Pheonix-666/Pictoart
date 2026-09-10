from typing import Tuple, Optional
import os
import cv2
import numpy as np
from PIL import Image
from src.art_engine.art_config import NATURAL_OVERLAP_ERODE

# ---------------------------------------------------------------------------
# rembg import fallback
# ---------------------------------------------------------------------------
try:
    from rembg import remove as rembg_remove
    _REMBG_AVAILABLE = True
except ImportError:
    _REMBG_AVAILABLE = False


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

    # ── Step 2: Face & Neck Landmark Detection ──────────────────────────────
    fx, fy, fw, fh = w // 4, int(h * 0.15), w // 2, int(h * 0.45)
    chin_y = fy + fh
    neck_bottom_y = min(h, chin_y + int(fh * 0.48))
    face_detected = False

    # Try YuNet face detector if model file exists
    yunet_path = "yunet_face.onnx"
    if os.path.exists(yunet_path):
        try:
            detector = cv2.FaceDetectorYN.create(yunet_path, "", (w, h), score_threshold=0.5)
            color_bgr = cv2.cvtColor(color_np, cv2.COLOR_RGB2BGR)
            _, faces = detector.detect(color_bgr)
            if faces is not None and len(faces) > 0:
                f = faces[0]
                fx, fy, fw, fh = int(f[0]), int(f[1]), int(f[2]), int(f[3])
                mouth_y = int((f[11] + f[13]) / 2)
                nose_y = int(f[9])
                chin_y = int(mouth_y + (mouth_y - nose_y) * 1.30)
                neck_bottom_y = min(h, chin_y + int(fh * 0.48))
                face_detected = True
        except Exception:
            pass

    if not face_detected:
        # Fallback to Haar Cascade
        if hasattr(cv2, 'CascadeClassifier'):
            try:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray_np, scaleFactor=1.1, minNeighbors=3, minSize=(60, 60))
                if len(faces) > 0:
                    largest = max(faces, key=lambda r: r[2] * r[3])
                    fx, fy, fw, fh = largest
                    chin_y = fy + int(fh * 1.05)
                    neck_bottom_y = min(h, chin_y + int(fh * 0.48))
                    face_detected = True
            except Exception:
                pass

    # ── Step 3: Natural Mask Construction (Head + Face + Neck) ──────────────
    head_mask = silhouette_mask.copy()
    head_mask[neck_bottom_y:, :] = 0

    # Clean neck boundary width
    neck_left = max(0, fx - int(fw * 0.10))
    neck_right = min(w, fx + fw + int(fw * 0.10))
    head_mask[chin_y:neck_bottom_y, :neck_left] = 0
    head_mask[chin_y:neck_bottom_y, neck_right:] = 0

    # Also detect skin pixels to ensure natural contours under chin
    ycrcb = cv2.cvtColor(color_np, cv2.COLOR_RGB2YCrCb)
    hsv = cv2.cvtColor(color_np, cv2.COLOR_RGB2HSV)
    skin_ycrcb = cv2.inRange(ycrcb, np.array([0, 130, 75]), np.array([255, 180, 130]))
    skin_hsv = cv2.inRange(hsv, np.array([0, 15, 50]), np.array([30, 180, 255]))
    skin = cv2.bitwise_and(skin_ycrcb, skin_hsv)
    skin = cv2.bitwise_and(skin, silhouette_mask)
    skin[neck_bottom_y:, :] = 0

    natural_mask = cv2.bitwise_or(head_mask, skin)

    # Smooth and unify natural mask
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
    natural_mask = cv2.morphologyEx(natural_mask, cv2.MORPH_CLOSE, close_kernel)
    natural_mask = cv2.bitwise_and(natural_mask, silhouette_mask)

    # ── Step 4: Clothing Mask ───────────────────────────────────────────────
    clothing_mask = cv2.bitwise_and(silhouette_mask, cv2.bitwise_not(natural_mask))

    return silhouette_mask, natural_mask, clothing_mask


def extract_silhouette_mask(gray_np: np.ndarray, color_np: np.ndarray) -> np.ndarray:
    """Legacy helper returning full silhouette mask."""
    silhouette_mask, _, _ = extract_masks(gray_np, color_np)
    return silhouette_mask
