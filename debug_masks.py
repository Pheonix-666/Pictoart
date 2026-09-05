"""
debug_masks.py — Standalone debug utility for PICTOART segmentation and sketch generation.

Usage:
    python debug_masks.py <photo_path> [output_dir]

Runs extract_masks() and render_pencil_sketch() on the supplied photo and writes:
    <output_dir>/silhouette_mask.png   — full person outline
    <output_dir>/face_mask.png         — face region
    <output_dir>/body_mask.png         — body / clothing region
    <output_dir>/mask_overview.png     — colour-coded composite overlay
    <output_dir>/pencil_lines.png      — extracted pencil contour strokes
    <output_dir>/sketch_portrait.png   — rendered artistic graphite sketch portrait
"""
import sys
import os

# Allow running from project root without installing as a package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np

from src.art_engine.preprocessor import preprocess_image
from src.art_engine.segmentation import extract_masks, save_debug_masks, _REMBG_AVAILABLE
from src.art_engine.sketch import extract_pencil_lines, render_full_sketch_portrait


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_masks.py <photo_path> [output_dir]")
        sys.exit(1)

    photo_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./debug_output"
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(photo_path):
        print(f"Error: file not found — {photo_path}")
        sys.exit(1)

    print(f"[Debug] rembg available: {_REMBG_AVAILABLE}")
    print(f"[Debug] Loading photo: {photo_path}")

    with open(photo_path, "rb") as f:
        photo_bytes = f.read()

    # Preprocess to 1200×1200
    gray_np, color_np, _ = preprocess_image(photo_bytes, target_size=(1200, 1200))

    print("[Debug] Running extract_masks()...")
    save_debug_masks(gray_np, color_np, output_dir=output_dir)

    silhouette_mask, _, _ = extract_masks(gray_np, color_np)

    # Save pencil lines
    lines = extract_pencil_lines(gray_np)
    lines_path = os.path.join(output_dir, "pencil_lines.png")
    cv2.imwrite(lines_path, lines)
    print(f"[Debug] Saved pencil lines: {lines_path}")

    # Render full sketch portrait
    sketch = render_full_sketch_portrait(gray_np, silhouette_mask, output_size=(1600, 1600))
    sketch_path = os.path.join(output_dir, "sketch_portrait.png")
    sketch.save(sketch_path)
    print(f"[Debug] Saved sketch portrait: {sketch_path}")

    print(f"[Debug] Done. Open '{output_dir}/' to inspect mask and sketch PNGs.")


if __name__ == "__main__":
    main()
