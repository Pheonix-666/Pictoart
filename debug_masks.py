"""
debug_masks.py — Standalone debug utility for PICTOART segmentation.

Usage:
    python debug_masks.py <photo_path> [output_dir]

Runs extract_masks() on the supplied photo and writes:
    <output_dir>/silhouette_mask.png   — full person outline
    <output_dir>/face_mask.png         — face region
    <output_dir>/body_mask.png         — body / clothing region
    <output_dir>/mask_overview.png     — colour-coded composite overlay

This lets you visually verify segmentation quality BEFORE any word-art
rendering runs, making it easy to catch failures on non-plain backgrounds.
"""
import sys
import os

# Allow running from project root without installing as a package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np

from src.art_engine.preprocessor import preprocess_image
from src.art_engine.segmentation import save_debug_masks, _REMBG_AVAILABLE


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_masks.py <photo_path> [output_dir]")
        sys.exit(1)

    photo_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./debug_output"

    if not os.path.exists(photo_path):
        print(f"Error: file not found — {photo_path}")
        sys.exit(1)

    print(f"[Debug] rembg available: {_REMBG_AVAILABLE}")
    print(f"[Debug] Loading photo: {photo_path}")

    with open(photo_path, "rb") as f:
        photo_bytes = f.read()

    # Preprocess to 1200×1200 — same resolution used in the worker pipeline
    gray_np, color_np, _ = preprocess_image(photo_bytes, target_size=(1200, 1200))

    print(f"[Debug] Running extract_masks() …")
    save_debug_masks(gray_np, color_np, output_dir=output_dir)

    from src.art_engine.segmentation import extract_masks
    from src.art_engine.density import create_shading_and_gradient_map, save_debug_overlays
    _, _, clothing_mask = extract_masks(gray_np, color_np)
    shading_map, grad_x, grad_y = create_shading_and_gradient_map(gray_np, clothing_mask)
    save_debug_overlays(color_np, clothing_mask, shading_map, grad_x, grad_y, output_dir=output_dir)

    print(f"[Debug] Done. Open '{output_dir}/' to inspect mask and density PNGs.")



if __name__ == "__main__":
    main()
