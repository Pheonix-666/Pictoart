"""
density.py — Shading Map & Gradient Field generation for PICTOART.

Extracts luminance from original photo inside clothing_mask, applies CLAHE
contrast normalization, and computes Sobel gradient fields to drive word-art
density, font sizing, and flow direction.
"""
import os
import cv2
import numpy as np
from typing import Tuple
from src.art_engine.art_config import DARK_AREA_THRESHOLD


def create_shading_and_gradient_map(
    gray_np: np.ndarray,
    clothing_mask: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes:
    1. shading_map: normalized float array [0.0, 1.0] where 1.0 = dark fold/shadow
                    and 0.0 = bright highlight or background.
    2. grad_x, grad_y: Sobel gradient direction components for word flow alignment.

    Includes automatic fallback for flat/low-variance clothing.
    """
    h, w = gray_np.shape

    # 1. CLAHE contrast enhancement inside clothing ROI
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray_np)

    # 2. Invert grayscale: dark pixels -> high values (1.0)
    inv_gray = 255.0 - enhanced_gray.astype(np.float32)
    shading_map = inv_gray / 255.0

    # Mask to clothing region
    mask_norm = (clothing_mask.astype(np.float32) / 255.0)
    shading_map = shading_map * mask_norm

    # Fallback: check variance inside clothing_mask
    mask_pixels = shading_map[clothing_mask > 0]
    if len(mask_pixels) > 0 and np.var(mask_pixels) < 0.005:
        # Flat solid clothing -> inject subtle synthetic gradient for visual depth
        y_grid, x_grid = np.ogrid[:h, :w]
        synthetic_grad = 0.5 + 0.3 * (y_grid / float(h))
        shading_map = shading_map * synthetic_grad
        shading_map = np.clip(shading_map, 0.0, 1.0)

    # Contrast curve for strong fold definitions
    shading_map = np.power(shading_map, 1.2)

    # 3. Compute Sobel gradients for word flow alignment
    grad_x = cv2.Sobel(shading_map, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(shading_map, cv2.CV_32F, 0, 1, ksize=3)

    return shading_map, grad_x, grad_y


def save_debug_overlays(
    color_np: np.ndarray,
    clothing_mask: np.ndarray,
    shading_map: np.ndarray,
    grad_x: np.ndarray,
    grad_y: np.ndarray,
    output_dir: str = "./debug_output"
) -> None:
    """
    Saves debug preview images:
    - shading_map.png: Visual grayscale map of fold/shadow density.
    - gradient_field.png: Color-coded vector flow overlay showing word rotation directions.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Shading map image
    shading_img = (shading_map * 255).astype(np.uint8)
    cv2.imwrite(os.path.join(output_dir, "shading_map.png"), shading_img)

    # Gradient direction flow visualization (HSV colorwheel mapping)
    magnitude, angle = cv2.cartToPolar(grad_x, grad_y, angleInDegrees=True)
    hsv = np.zeros((color_np.shape[0], color_np.shape[1], 3), dtype=np.uint8)
    hsv[..., 0] = (angle / 2).astype(np.uint8)  # Hue = direction
    hsv[..., 1] = 255                          # Saturation = max
    hsv[..., 2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    flow_bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    flow_bgr[clothing_mask == 0] = 0
    cv2.imwrite(os.path.join(output_dir, "gradient_field.png"), flow_bgr)

    print(f"[Debug] Saved shading_map.png and gradient_field.png to '{output_dir}'.")


def create_density_map(gray_np: np.ndarray, mask_np: np.ndarray) -> np.ndarray:
    """Legacy compatibility helper returning shading density map."""
    shading_map, _, _ = create_shading_and_gradient_map(gray_np, mask_np)
    return shading_map

