"""
sketch.py — High-fidelity artistic pencil sketch portrait generation engine.

Transforms a preprocessed photo and subject mask into an authentic graphite pencil
sketch featuring:
1. Multi-scale Difference-of-Gaussians (DoG) pencil line extraction (eyes, facial contours, hair, clothes).
2. Edge-preserving bilateral filtering to eliminate sensor/skin noise.
3. Classic Color Dodge pencil tonal shading for rich graphite gradations.
4. Depth-mapped shadow contrast curve for lifelike realism and likeness.
5. Hand-drawn outer boundary pencil stroke.
6. Seamless composition onto fine-art textured sketch paper or clean alpha background.
"""
import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
from src.art_engine.art_config import (
    SKETCH_BLUR_KERNEL,
    SKETCH_GAMMA,
    DOG_SIGMA1,
    DOG_SIGMA2,
    DODGE_WEIGHT,
    TONAL_WEIGHT,
    PENCIL_LINE_WEIGHT,
    SILHOUETTE_FEATHER_PX,
    BOUNDARY_DARK_WEIGHT,
    PAPER_COLOR,
    GRAPHITE_TINT,
)


def extract_pencil_lines(
    gray_np: np.ndarray,
    sigma1: float = DOG_SIGMA1,
    sigma2: float = DOG_SIGMA2
) -> np.ndarray:
    """
    Extracts crisp, organic pencil contour lines using Difference of Gaussians (DoG)
    combined with edge-preserving bilateral filtering to avoid skin speckle/noise.
    Returns grayscale array (0 = black pencil stroke, 255 = white paper).
    """
    # 1. Bilateral smoothing to preserve sharp contours while eliminating sensor noise
    smoothed = cv2.bilateralFilter(gray_np, d=7, sigmaColor=45, sigmaSpace=45)

    # 2. Difference of Gaussians (DoG) for multi-scale pencil edge response
    g1 = cv2.GaussianBlur(smoothed.astype(np.float32), (0, 0), sigmaX=sigma1)
    g2 = cv2.GaussianBlur(smoothed.astype(np.float32), (0, 0), sigmaX=sigma2)
    dog = g1 - g2

    # 3. Soft threshold / sigmoid contrast curve to simulate graphite pencil pressure
    dog_norm = dog / (np.max(np.abs(dog)) + 1e-6)
    # Hyperbolic tangent gives smooth, natural line tapering like real graphite
    lines = 1.0 - np.clip(np.tanh(dog_norm * 4.5), 0, 1.0)
    lines_uint8 = (lines * 255.0).astype(np.uint8)

    # Invert so lines are dark on light background
    return lines_uint8


def render_pencil_sketch(
    gray_np: np.ndarray,
    mask_np: np.ndarray,
    output_size: Optional[Tuple[int, int]] = None,
    natural_mask: Optional[np.ndarray] = None,
    clothing_mask: Optional[np.ndarray] = None
) -> Image.Image:
    """
    Renders the full subject into a rich graphite pencil sketch portrait.
    Returns an RGBA PIL Image with pencil tones in RGB and soft-feathered mask in Alpha.
    """
    # 1. Edge-preserving bilateral filter
    smooth_gray = cv2.bilateralFilter(gray_np, d=9, sigmaColor=50, sigmaSpace=50)

    # 2. Classic Color Dodge pencil shading
    inv_smooth = 255 - smooth_gray
    ksize = SKETCH_BLUR_KERNEL if SKETCH_BLUR_KERNEL % 2 == 1 else SKETCH_BLUR_KERNEL + 1
    blurred_inv = cv2.GaussianBlur(inv_smooth, (ksize, ksize), 0)
    # Color dodge formula: smooth_gray / (255 - blurred_inv) * 256
    sketch_dodge = cv2.divide(smooth_gray, 255 - blurred_inv, scale=256)

    # 3. Blend dodge highlights with smoothed grayscale to preserve depth & facial likeness
    dodge_w = DODGE_WEIGHT
    tonal_w = TONAL_WEIGHT
    tonal_sketch = cv2.addWeighted(sketch_dodge, dodge_w, smooth_gray, tonal_w, 0)

    # 4. Multiply with fine pencil contour lines
    lines = extract_pencil_lines(gray_np)
    # Normalize lines from [0, 255] to [0.0, 1.0]
    lines_factor = lines.astype(np.float32) / 255.0
    combined = (tonal_sketch.astype(np.float32) * (1.0 - PENCIL_LINE_WEIGHT * (1.0 - lines_factor)))
    combined = np.clip(combined, 0, 255).astype(np.uint8)

    # 5. Contrast & gamma adjustment for rich graphite darks
    norm = combined.astype(np.float32) / 255.0
    darkened = np.power(norm, SKETCH_GAMMA) * 255.0
    final_sketch = np.clip(darkened, 0, 255).astype(np.uint8)

    # 6. Clean outer silhouette boundary outline (accentuate subject perimeter like a hand sketch)
    bin_mask = (mask_np > 80).astype(np.uint8) * 255
    morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    outer_boundary = cv2.morphologyEx(bin_mask, cv2.MORPH_GRADIENT, morph_kernel)
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    boundary_mask = cv2.dilate(outer_boundary, dilate_kernel)

    boundary_factor = (boundary_mask.astype(np.float32) / 255.0) * BOUNDARY_DARK_WEIGHT
    final_sketch = (final_sketch.astype(np.float32) * (1.0 - boundary_factor)).clip(0, 255).astype(np.uint8)

    # 7. Soft edge-feathering on the alpha mask so the sketch merges organically into background
    feather_k = SILHOUETTE_FEATHER_PX if SILHOUETTE_FEATHER_PX % 2 == 1 else SILHOUETTE_FEATHER_PX + 1
    feathered_mask = cv2.GaussianBlur(mask_np.astype(np.float32), (feather_k, feather_k), 0)
    feathered_mask = np.clip(feathered_mask, 0, 255).astype(np.uint8)

    # 8. Assemble RGBA image
    h, w = gray_np.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = final_sketch
    rgba[:, :, 1] = final_sketch
    rgba[:, :, 2] = final_sketch
    rgba[:, :, 3] = feathered_mask

    pil_sketch = Image.fromarray(rgba, mode="RGBA")

    if output_size is not None and output_size != (w, h):
        pil_sketch = pil_sketch.resize(output_size, Image.Resampling.LANCZOS)

    return pil_sketch


def render_full_sketch_portrait(
    gray_np: np.ndarray,
    mask_np: np.ndarray,
    output_size: Tuple[int, int] = (1600, 1600),
    paper_color: Tuple[int, int, int] = PAPER_COLOR
) -> Image.Image:
    """
    Renders the complete artistic pencil sketch portrait layered onto a fine-art paper canvas.
    """
    # Render pencil sketch with alpha mask
    sketch_rgba = render_pencil_sketch(
        gray_np=gray_np,
        mask_np=mask_np,
        output_size=output_size
    )

    # Create background paper canvas
    w, h = output_size
    paper = Image.new("RGBA", (w, h), (*paper_color, 255))

    # Composite pencil sketch onto the paper canvas
    composited = Image.alpha_composite(paper, sketch_rgba).convert("RGB")
    return composited
