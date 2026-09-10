import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
from src.art_engine.art_config import ART_RULES, SKETCH_BLUR_KERNEL, SKETCH_GAMMA


def _create_hatch_texture(shape: Tuple[int, int], angle: float, spacing: int, thickness: int = 1) -> np.ndarray:
    """Generates a seamless rotated parallel-line pencil hatching pattern."""
    h, w = shape
    diag = int(np.sqrt(h * h + w * w)) + 30
    pad_canvas = np.zeros((diag * 2, diag * 2), dtype=np.float32)
    for y in range(0, diag * 2, max(1, spacing)):
        cv2.line(pad_canvas, (0, y), (diag * 2, y), 1.0, thickness)
    M = cv2.getRotationMatrix2D((diag, diag), angle, 1.0)
    rotated = cv2.warpAffine(pad_canvas, M, (diag * 2, diag * 2), flags=cv2.INTER_LINEAR)
    start_y = diag - h // 2
    start_x = diag - w // 2
    return rotated[start_y:start_y + h, start_x:start_x + w]


def render_pencil_sketch(
    gray_np: np.ndarray,
    mask_np: np.ndarray,
    output_size: Optional[Tuple[int, int]] = None,
    natural_mask: Optional[np.ndarray] = None,
    clothing_mask: Optional[np.ndarray] = None
) -> Image.Image:
    """
    Renders subject region as an authentic, high-detail cross-hatched pencil etching
    calibrated to match the sample reference portraits:
    1. Edge-preserving bilateral filter eliminates sensor noise while retaining crisp anatomical planes.
    2. Multi-scale Canny & Difference of Gaussians (DoG) for fine, organic pencil outlines.
    3. Continuous multi-directional cross-hatching textures (-35 deg, 52 deg, -75 deg, 15 deg).
    4. Hair-strand micro-detail extraction for rich directional hair rendering.
    5. Smooth gamma contrast for rich graphite blacks and clean paper highlights.
    """
    h, w = gray_np.shape

    # 1. Edge-preserving filtering
    smooth = cv2.bilateralFilter(gray_np, d=9, sigmaColor=55, sigmaSpace=55)
    norm = smooth.astype(np.float32) / 255.0  # 1.0 = white, 0.0 = black

    # 2. Multi-angle hatching textures
    h1 = _create_hatch_texture((h, w), -35.0, spacing=4, thickness=1)
    h2 = _create_hatch_texture((h, w), 52.0, spacing=4, thickness=1)
    h3 = _create_hatch_texture((h, w), -75.0, spacing=4, thickness=1)
    h4 = _create_hatch_texture((h, w), 15.0, spacing=3, thickness=1)

    # 3. Continuous tonal ramps for smooth transition across facial contours
    darkness = 1.0 - norm
    w1 = np.clip((darkness - 0.12) / 0.35, 0, 1)  # light tones
    w2 = np.clip((darkness - 0.32) / 0.35, 0, 1)  # midtones
    w3 = np.clip((darkness - 0.52) / 0.30, 0, 1)  # shadows
    w4 = np.clip((darkness - 0.70) / 0.25, 0, 1)  # deep darks

    # 4. Color Dodge sketch layer for organic paper texture
    inv = 255 - smooth
    ksize = SKETCH_BLUR_KERNEL if SKETCH_BLUR_KERNEL % 2 == 1 else SKETCH_BLUR_KERNEL + 1
    blur_inv = cv2.GaussianBlur(inv, (ksize, ksize), 0)
    dodge = cv2.divide(smooth, np.maximum(1, 255 - blur_inv), scale=256)

    # 5. Continuous graphite ink blending
    ink = (h1 * w1 * 0.32 + h2 * w2 * 0.32 + h3 * w3 * 0.28 + h4 * w4 * 0.28 + (darkness ** 1.4) * 0.55)
    ink = np.clip(ink, 0, 1)
    sketch_raw = ((1.0 - ink) * 255.0).astype(np.uint8)

    # Blend hatching with dodge wash
    blended = cv2.addWeighted(sketch_raw, 0.75, dodge, 0.25, 0)

    # 6. Hair strand micro-detail extraction
    hair_detail = cv2.absdiff(gray_np, smooth)
    _, hair_strands = cv2.threshold(hair_detail, 8, 255, cv2.THRESH_BINARY)
    hair_strands = cv2.bitwise_and(hair_strands, (norm < 0.38).astype(np.uint8) * 255)
    blended[hair_strands > 0] = np.minimum(blended[hair_strands > 0], 20)

    # 7. Crisp pencil edge contours (eyes, pupils, smile, nostrils)
    edges_canny = cv2.Canny(smooth, 25, 85)
    blended[edges_canny > 0] = np.minimum(blended[edges_canny > 0], 15)

    # Difference of Gaussians (DoG) for secondary contour definition
    g1 = cv2.GaussianBlur(smooth, (3, 3), 0)
    g2 = cv2.GaussianBlur(smooth, (7, 7), 0)
    dog = cv2.subtract(g2, g1)
    _, dog_thresh = cv2.threshold(dog, 5, 255, cv2.THRESH_BINARY)
    blended[dog_thresh > 0] = np.minimum(blended[dog_thresh > 0], 25)

    # 8. Gamma curve for rich tonal contrast
    gamma_lut = np.array(
        [min(255, int(255.0 * (i / 255.0) ** SKETCH_GAMMA)) for i in range(256)],
        dtype=np.uint8
    )
    blended = cv2.LUT(blended, gamma_lut)

    # 9. Build RGBA image masked to natural_mask
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = blended
    rgba[:, :, 1] = blended
    rgba[:, :, 2] = blended
    rgba[:, :, 3] = mask_np

    pil_sketch = Image.fromarray(rgba, mode="RGBA")

    if output_size is not None and output_size != (w, h):
        pil_sketch = pil_sketch.resize(output_size, Image.Resampling.LANCZOS)

    return pil_sketch
