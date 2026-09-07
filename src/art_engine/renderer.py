"""
renderer.py — Typographic word-art renderer for PICTOART clothing/body region.

Generates dense, structured typographic blocks (both horizontal and vertical)
matching authentic editorial letterpress/masonry portrait layouts with tone-adaptive
inversion (white text on dark backgrounds in collar/folds) and crisp garment seam overlays.
"""
from __future__ import annotations

import math
import os
import random
from typing import Optional, Tuple, List, Dict, Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.art_engine.art_config import (
    FONT_PATHS,
    PRIMARY_COLOR,
    ACCENT_COLOR,
    ART_RULES,
)
from src.art_engine.words import BIG_WORDS, SHORT_WORDS

# ── Font loading & caching ────────────────────────────────────────────────────
_font_cache: dict[int, ImageFont.FreeTypeFont] = {}
_resolved_font_path: Optional[str] = None


def _resolve_font_path() -> Optional[str]:
    for path in FONT_PATHS:
        if os.path.exists(path):
            return path
    return None


def get_font(size: int) -> ImageFont.FreeTypeFont:
    """
    Load (and cache) a TrueType font at *size* points.
    Falls back to PIL's built-in bitmap font if no TTF file is found.
    Also imported by composer.py — name must stay stable.
    """
    global _resolved_font_path

    if size in _font_cache:
        return _font_cache[size]

    if _resolved_font_path is None:
        _resolved_font_path = _resolve_font_path()

    try:
        font = (
            ImageFont.truetype(_resolved_font_path, size)
            if _resolved_font_path
            else ImageFont.load_default()
        )
    except Exception:
        font = ImageFont.load_default()

    _font_cache[size] = font
    return font


def render_word_art_portrait(
    mask_np: np.ndarray,
    density_map: np.ndarray,
    text_pool: List[Tuple[str, int]],
    grad_x: Optional[np.ndarray] = None,
    grad_y: Optional[np.ndarray] = None,
    output_size: Tuple[int, int] = (1600, 1600),
    natural_mask: Optional[np.ndarray] = None,
    orig_gray: Optional[np.ndarray] = None,
) -> Image.Image:
    """
    Renders clothing as dense, structured typographic blocks (horizontal and vertical)
    with tone-adaptive inversion and garment seam overlays calibrated on reference samples.

    Public API called by jobs.py and tests/test_core.py.
    """
    h, w = mask_np.shape

    # Normalize mask
    bin_mask = (mask_np > 100).astype(np.uint8) * 255
    total_mask_px = int(np.count_nonzero(bin_mask))

    if total_mask_px == 0:
        return Image.new("RGBA", output_size, (0, 0, 0, 0))

    # Base RGBA canvas (starts transparent so text letters and ink leave natural negative space)
    cloth_pil = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # Load rules
    typo_cfg = ART_RULES.get("typography", {})
    inversion_cfg = typo_cfg.get("tone_inversion", {})
    seam_cfg = typo_cfg.get("garment_seams", {})

    dark_density_cutoff = float(inversion_cfg.get("shading_density_cutoff", 0.60))
    collar_prox = int(inversion_cfg.get("collar_proximity_px", 55))
    collar_depth = int(inversion_cfg.get("collar_depth_px", 260))
    inv_threshold = float(inversion_cfg.get("inverted_block_threshold", 0.35))
    box_fill = tuple(inversion_cfg.get("box_fill_rgba", [18, 18, 18, 255]))
    text_inv_color = tuple(inversion_cfg.get("text_inverted_rgba", [255, 255, 255, 255]))
    text_std_color = tuple(inversion_cfg.get("text_standard_rgba", [15, 15, 15, 255]))

    # Edge seams and contours of clothing
    if orig_gray is not None:
        cloth_gray = cv2.bitwise_and(orig_gray, bin_mask)
    else:
        cloth_gray = (np.clip(1.0 - density_map, 0, 1) * 255).astype(np.uint8)
        cloth_gray = cv2.bitwise_and(cloth_gray, bin_mask)

    blur_k = int(seam_cfg.get("blur_ksize", 13))
    canny_l = int(seam_cfg.get("canny_low", 50))
    canny_h = int(seam_cfg.get("canny_high", 140))
    min_comp_area = int(seam_cfg.get("min_component_area", 35))
    seam_color = tuple(seam_cfg.get("line_rgba", [15, 15, 15, 255]))

    blurred_cloth = cv2.GaussianBlur(cloth_gray, (blur_k, blur_k), 0)
    raw_edges = cv2.Canny(blurred_cloth, canny_l, canny_h)
    raw_edges = cv2.bitwise_and(raw_edges, bin_mask)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(raw_edges)
    cloth_edges = np.zeros_like(raw_edges)
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] > min_comp_area:
            cloth_edges[labels == i] = 255

    # Detect dark zones (collar lapels, deep shadows, fold creases)
    if natural_mask is not None:
        dist_to_nat = cv2.distanceTransform((natural_mask == 0).astype(np.uint8), cv2.DIST_L2, 5)
        y_cloth, _ = np.where(bin_mask > 0)
        top_cloth_y = y_cloth.min() if len(y_cloth) > 0 else 0
        collar_lapel_mask = (bin_mask > 0) & (dist_to_nat < collar_prox) & (np.arange(h)[:, None] < top_cloth_y + collar_depth)
    else:
        collar_lapel_mask = np.zeros((h, w), dtype=bool)

    # Dark clothing mask from density map (> dark_density_cutoff) or collar lapels
    dark_clothing_mask = (density_map > dark_density_cutoff) | collar_lapel_mask

    # Pool organization: Big words for large spaces / headlines / subheadings, Short words for small spaces / body / fine
    all_phrases = [p for p, _ in text_pool]
    # Filter out any leftover experience strings if any
    all_phrases = [p for p in all_phrases if "YEAR" not in p and "EXPERIENCE" not in p]

    # Large spaces (headlines & prominent blocks)
    large_headlines = [p for p in all_phrases if len(p) >= 12] + BIG_WORDS
    med_phrases = [p for p in all_phrases if 7 <= len(p) <= 20] + BIG_WORDS

    # Small spaces (body & fine detail passes)
    small_phrases = [p for p in all_phrases if len(p) <= 8 and " " not in p] + SHORT_WORDS

    # Hierarchy passes from rules
    hierarchy_rules = typo_cfg.get("font_hierarchy", [
        {"tier": "headline",   "font_size": 28, "step_y": 26, "step_x": 16, "min_occupancy": 0.80, "vertical_prob": 0.12, "max_overlap": 0.20},
        {"tier": "subheading", "font_size": 18, "step_y": 16, "step_x": 12, "min_occupancy": 0.76, "vertical_prob": 0.22, "max_overlap": 0.30},
        {"tier": "body",       "font_size": 12, "step_y": 11, "step_x": 8,  "min_occupancy": 0.70, "vertical_prob": 0.32, "max_overlap": 0.45},
        {"tier": "fine",       "font_size": 8,  "step_y": 7,  "step_x": 5,  "min_occupancy": 0.62, "vertical_prob": 0.38, "max_overlap": 0.50},
    ])

    pool_map = {
        "headline": large_headlines,
        "subheading": med_phrases,
        "body": small_phrases,
        "fine": small_phrases,
    }

    occupied = np.zeros((h, w), dtype=bool)
    rng = random.Random(42)

    for p_idx, p_config in enumerate(hierarchy_rules):
        tier = p_config.get("tier", "body")
        pool = pool_map.get(tier, small_phrases)
        f_size = int(p_config.get("font_size", 12))
        font = get_font(f_size)
        step_y = int(p_config.get("step_y", 12))
        step_x = int(p_config.get("step_x", 8))
        vert_prob = float(p_config.get("vertical_prob", 0.20))
        min_occ = float(p_config.get("min_occupancy", 0.70))
        max_overlap = float(p_config.get("max_overlap", 0.35))

        for y in range(0, h - step_y, step_y):
            for x in range(0, w - 15, step_x):
                cy = min(h - 1, y + step_y // 2)
                cx = min(w - 1, x + 10)
                if bin_mask[cy, cx] == 0:
                    continue
                if occupied[cy, cx] and p_idx < 2:
                    continue

                is_vert = rng.random() < vert_prob
                phrase = rng.choice(pool)

                bbox = font.getbbox(phrase)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

                if is_vert:
                    bw, bh = th + 4, tw + 4
                else:
                    bw, bh = tw + 4, th + 4

                if x + bw >= w or y + bh >= h:
                    continue

                sub_mask = bin_mask[y:y+bh, x:x+bw]
                if np.count_nonzero(sub_mask) < min_occ * (bw * bh):
                    continue

                sub_occ = occupied[y:y+bh, x:x+bw]
                if np.count_nonzero(sub_occ) > max_overlap * (bw * bh):
                    continue

                # Tone check
                sub_dark = dark_clothing_mask[y:y+bh, x:x+bw]
                dark_ratio = np.count_nonzero(sub_dark) / max(1, bw * bh)
                is_dark_block = dark_ratio > inv_threshold

                # Render patch
                if is_vert:
                    patch = Image.new("RGBA", (tw + 4, th + 4), (0, 0, 0, 0))
                    pdraw = ImageDraw.Draw(patch)
                    if is_dark_block:
                        pdraw.rectangle([0, 0, tw + 4, th + 4], fill=box_fill)
                        pdraw.text((2 - bbox[0], 2 - bbox[1]), phrase, fill=text_inv_color, font=font)
                    else:
                        pdraw.text((2 - bbox[0], 2 - bbox[1]), phrase, fill=text_std_color, font=font)
                    patch = patch.rotate(90, expand=True)
                else:
                    patch = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
                    pdraw = ImageDraw.Draw(patch)
                    if is_dark_block:
                        pdraw.rectangle([0, 0, bw, bh], fill=box_fill)
                        pdraw.text((2 - bbox[0], 2 - bbox[1]), phrase, fill=text_inv_color, font=font)
                    else:
                        pdraw.text((2 - bbox[0], 2 - bbox[1]), phrase, fill=text_std_color, font=font)

                cloth_pil.paste(patch, (x, y), patch)
                occupied[y:y+bh, x:x+bw] = True

    cloth_arr = np.array(cloth_pil)
    # Mask strictly to clothing region
    cloth_arr[:, :, 3] = np.where(bin_mask > 0, cloth_arr[:, :, 3], 0)

    # Overlay clothing seam & fold edges for realistic garment structure
    if np.count_nonzero(cloth_edges) > 0:
        fold_lines = (cloth_edges > 0) & (bin_mask > 0)
        cloth_arr[fold_lines, 0] = seam_color[0]
        cloth_arr[fold_lines, 1] = seam_color[1]
        cloth_arr[fold_lines, 2] = seam_color[2]
        cloth_arr[fold_lines, 3] = seam_color[3]

    # Dark collar outline
    collar_contour = cv2.morphologyEx(bin_mask, cv2.MORPH_GRADIENT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    cloth_arr[collar_contour > 0, 0] = seam_color[0]
    cloth_arr[collar_contour > 0, 1] = seam_color[1]
    cloth_arr[collar_contour > 0, 2] = seam_color[2]
    cloth_arr[collar_contour > 0, 3] = seam_color[3]

    result = Image.fromarray(cloth_arr)

    if output_size is not None and output_size != (w, h):
        result = result.resize(output_size, Image.Resampling.LANCZOS)

    return result
