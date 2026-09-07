import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
from src.art_engine.art_config import ART_RULES, SKETCH_BLUR_KERNEL, SKETCH_GAMMA


def _create_hatch_texture(shape: Tuple[int, int], angle: float, spacing: int, thickness: int = 1) -> np.ndarray:
    """Generates a seamless rotated parallel-line pencil hatching pattern."""
    h, w = shape
    diag = int(np.sqrt(h * h + w * w)) + 30
    pad_canvas = np.zeros((diag * 2, diag * 2), dtype=np.uint8)
    for y in range(0, diag * 2, max(1, spacing)):
        cv2.line(pad_canvas, (0, y), (diag * 2, y), 255, thickness)
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
    3. Multi-directional cross-hatching textures (-35 deg, 52 deg, -75 deg, 15 deg) scaled by local tonal density.
    4. Hair-strand micro-detail extraction for rich directional hair rendering.
    5. Organic paper tooth micro-texture and soft graphite dodge blend for 100% photographic likeness.
    """
    h, w = gray_np.shape

    # Extract hatching rules
    h_rules = ART_RULES.get("hatching", {})
    angles = h_rules.get("angles_deg", [-35.0, 52.0, -75.0, 15.0])
    line_spacing = int(h_rules.get("line_spacing_px", 4))
    line_thick = int(h_rules.get("line_thickness_px", 1))

    edges_cfg = h_rules.get("edge_preservation", {})
    canny_l = int(edges_cfg.get("canny_low", 28))
    canny_h = int(edges_cfg.get("canny_high", 92))
    dog_k1 = int(edges_cfg.get("dog_kernel_1", 3))
    dog_k2 = int(edges_cfg.get("dog_kernel_2", 7))
    dog_thresh_val = int(edges_cfg.get("dog_threshold", 5))

    tex_cfg = h_rules.get("graphite_texture", {})
    hatch_w = float(tex_cfg.get("hatch_weight", 0.72))
    dodge_w = float(tex_cfg.get("dodge_weight", 0.28))
    tooth_noise = float(tex_cfg.get("paper_tooth_noise", 0.05))

    tone_cfg = h_rules.get("tone_cutoffs", {})
    light_range = tone_cfg.get("light", [0.65, 0.82])
    mid_range = tone_cfg.get("mid", [0.40, 0.65])
    shadow_range = tone_cfg.get("shadow", [0.18, 0.40])
    dark_cutoff = float(tone_cfg.get("deep_dark", 0.18))

    # 1. Edge-preserving filtering (stronger at 1600 px — removes sensor noise while keeping anatomical planes)
    smooth = cv2.bilateralFilter(gray_np, d=9, sigmaColor=55, sigmaSpace=55)

    # 2. Crisp anatomical contours
    edges_canny = cv2.Canny(smooth, canny_l, canny_h)

    # Difference of Gaussians for soft pencil shading contours
    g1 = cv2.GaussianBlur(smooth, (dog_k1, dog_k1), 0)
    g2 = cv2.GaussianBlur(smooth, (dog_k2, dog_k2), 0)
    dog = cv2.subtract(g2, g1)
    _, dog_thresh = cv2.threshold(dog, dog_thresh_val, 255, cv2.THRESH_BINARY)

    # Color Dodge sketch layer
    inv = 255 - smooth
    ksize = SKETCH_BLUR_KERNEL if SKETCH_BLUR_KERNEL % 2 == 1 else SKETCH_BLUR_KERNEL + 1
    blur_inv = cv2.GaussianBlur(inv, (ksize, ksize), 0)
    dodge = cv2.divide(smooth, np.maximum(1, 255 - blur_inv), scale=256)

    # 3. Fine hatching textures for 4 density tiers
    a1, a2, a3, a4 = angles[0], angles[1], angles[2], angles[3]
    hatch1 = _create_hatch_texture((h, w), a1, spacing=line_spacing, thickness=line_thick)
    hatch2 = _create_hatch_texture((h, w), a2, spacing=line_spacing, thickness=line_thick)
    hatch3 = _create_hatch_texture((h, w), a3, spacing=max(2, line_spacing - 1), thickness=line_thick)
    hatch4 = _create_hatch_texture((h, w), a4, spacing=line_spacing, thickness=line_thick)

    norm_tone = smooth.astype(np.float32) / 255.0

    # Start with crisp white paper
    sketch = np.full((h, w), 255, dtype=np.uint8)

    # Subtle light tones: fine single hatching
    mask_light = (norm_tone >= light_range[0]) & (norm_tone < light_range[1])
    sketch[mask_light & (hatch1 > 0)] = 175

    # Midtones: cross-hatching (2 directions)
    mask_mid = (norm_tone >= mid_range[0]) & (norm_tone < mid_range[1])
    sketch[mask_mid & (hatch1 > 0)] = 135
    sketch[mask_mid & (hatch2 > 0)] = 95

    # Shadows: triple cross-hatching + tone shading
    mask_shadow = (norm_tone >= shadow_range[0]) & (norm_tone < shadow_range[1])
    sketch[mask_shadow] = np.clip(smooth[mask_shadow] * 0.6 + 45, 0, 255).astype(np.uint8)
    sketch[mask_shadow & (hatch1 > 0)] = 65
    sketch[mask_shadow & (hatch2 > 0)] = 45
    sketch[mask_shadow & (hatch3 > 0)] = 25

    # Very dark / hair / pupils: dense multi-directional graphite texture
    mask_dark = norm_tone < dark_cutoff
    sketch[mask_dark] = np.clip(smooth[mask_dark] * 0.5 + 10, 0, 255).astype(np.uint8)
    sketch[mask_dark & (hatch3 > 0)] = 15
    sketch[mask_dark & (hatch4 > 0)] = 8

    # Hair strand micro-detail extraction
    hair_detail = cv2.absdiff(gray_np, smooth)
    _, hair_strands = cv2.threshold(hair_detail, 10, 255, cv2.THRESH_BINARY)
    hair_strands = cv2.bitwise_and(hair_strands, (norm_tone < 0.35).astype(np.uint8) * 255)
    sketch[hair_strands > 0] = np.minimum(sketch[hair_strands > 0], 25)

    # Blend hatching with soft Dodge sketch for organic graphite shading
    blended = cv2.addWeighted(sketch, hatch_w, dodge, dodge_w, 0)

    # Organic graphite paper tooth micro-texture (adds hand-drawn tactile grain)
    if tooth_noise > 0:
        rng = np.random.RandomState(42)
        grain = rng.normal(0, tooth_noise * 255.0, (h, w)).astype(np.float32)
        blended_f = np.clip(blended.astype(np.float32) + grain, 0, 255).astype(np.uint8)
        # Keep pure highlights clean
        blended = np.where(blended > 245, blended, blended_f)

    # Apply gamma correction for proper tonal depth (SKETCH_GAMMA was configured but never applied)
    gamma_lut = np.array(
        [min(255, int(255.0 * (i / 255.0) ** SKETCH_GAMMA)) for i in range(256)],
        dtype=np.uint8
    )
    blended = cv2.LUT(blended, gamma_lut)

    # Burn in crisp pencil edge lines
    blended[edges_canny > 0] = np.minimum(blended[edges_canny > 0], 18)
    blended[dog_thresh > 0] = np.minimum(blended[dog_thresh > 0], 30)

    # Build RGBA image
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = blended
    rgba[:, :, 1] = blended
    rgba[:, :, 2] = blended
    rgba[:, :, 3] = mask_np

    pil_sketch = Image.fromarray(rgba, mode="RGBA")

    if output_size is not None and output_size != (w, h):
        pil_sketch = pil_sketch.resize(output_size, Image.Resampling.LANCZOS)

    return pil_sketch
