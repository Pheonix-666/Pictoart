import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
from src.art_engine.art_config import SKETCH_BLUR_KERNEL, SKETCH_GAMMA

def render_pencil_sketch(
    gray_np: np.ndarray,
    mask_np: np.ndarray,
    output_size: Optional[Tuple[int, int]] = None,
    natural_mask: Optional[np.ndarray] = None,
    clothing_mask: Optional[np.ndarray] = None
) -> Image.Image:
    """
    Renders subject region as a dark, detailed pencil sketch with reinforced,
    darkened boundary outlines for the face, body, and major features:
    1. Color dodge with Gaussian kernel captures fine skin texture and hair.
    2. Adaptive Gaussian edge detection adds crisp details around eyes, lips, and hair strands.
    3. Morphological gradient & Canny extraction locate outer boundaries of face, neck, and body.
    4. Dark boundary overlay darkens the perimeter of face and clothing for prominent definition.
    5. Gamma contrast curve darkens stroke tones for rich depth.
    """
    # 1. Invert grayscale & apply fine-detail Gaussian blur
    inv_gray = 255 - gray_np
    ksize = SKETCH_BLUR_KERNEL if SKETCH_BLUR_KERNEL % 2 == 1 else SKETCH_BLUR_KERNEL + 1
    blurred = cv2.GaussianBlur(inv_gray, (ksize, ksize), 0)

    # 2. Color dodge blend
    sketch_dodge = cv2.divide(gray_np, 255 - blurred, scale=256)

    # 3. Fine adaptive edge overlay for eyes, nose, lips & texture
    adaptive_edges = cv2.adaptiveThreshold(
        gray_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 9, 2
    )

    # Blend dodge sketch with adaptive edges for sharper details
    sketch = cv2.addWeighted(sketch_dodge, 0.70, adaptive_edges, 0.30, 0)

    # 4. Extract boundary outlines for face and body
    morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    
    # Outer body/silhouette perimeter
    bin_mask = (mask_np > 100).astype(np.uint8) * 255
    body_boundary = cv2.morphologyEx(bin_mask, cv2.MORPH_GRADIENT, morph_kernel)

    # Face perimeter (if provided)
    face_boundary = np.zeros_like(bin_mask)
    if natural_mask is not None:
        bin_face = (natural_mask > 100).astype(np.uint8) * 255
        face_boundary = cv2.morphologyEx(bin_face, cv2.MORPH_GRADIENT, morph_kernel)

    # Clothing perimeter & major inner contours (if provided)
    clothing_boundary = np.zeros_like(bin_mask)
    if clothing_mask is not None:
        bin_cloth = (clothing_mask > 100).astype(np.uint8) * 255
        clothing_boundary = cv2.morphologyEx(bin_cloth, cv2.MORPH_GRADIENT, morph_kernel)

    # Key anatomical Canny edges (jawline, lapels, collar, eyes, nose)
    canny_edges = cv2.Canny(gray_np, 40, 120)

    # Combine boundaries and expand slightly for bold dark lines
    combined_boundaries = cv2.bitwise_or(body_boundary, face_boundary)
    combined_boundaries = cv2.bitwise_or(combined_boundaries, clothing_boundary)
    combined_boundaries = cv2.bitwise_or(combined_boundaries, canny_edges)
    
    # Dilate boundary mask slightly for strong stroke width
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    dark_boundary_mask = cv2.dilate(combined_boundaries, dilate_kernel)

    # 5. Burn/darken sketch pixels along boundary outlines
    boundary_factor = (dark_boundary_mask.astype(np.float32) / 255.0) * 0.75
    sketch_burned = sketch.astype(np.float32) * (1.0 - boundary_factor)
    sketch = np.clip(sketch_burned, 0, 255).astype(np.uint8)

    # 6. Gamma contrast curve to make sketch darker & more dramatic
    sketch_norm = sketch.astype(np.float32) / 255.0
    sketch_dark = np.power(sketch_norm, SKETCH_GAMMA) * 255.0
    sketch = np.clip(sketch_dark, 0, 255).astype(np.uint8)

    h, w = gray_np.shape

    # Build RGBA image (sketch intensity in RGB, mask_np in Alpha)
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = sketch
    rgba[:, :, 1] = sketch
    rgba[:, :, 2] = sketch
    rgba[:, :, 3] = mask_np

    pil_sketch = Image.fromarray(rgba, mode="RGBA")

    if output_size is not None and output_size != (w, h):
        pil_sketch = pil_sketch.resize(output_size, Image.Resampling.LANCZOS)

    return pil_sketch

