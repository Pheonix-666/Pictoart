"""
renderer.py — Word-Art Placement Engine for PICTOART.

Overhauled placement algorithm:
1. Shading Map drives font size and density (darker = denser/smaller, lighter = sparser/larger).
2. Sobel Gradient Field drives word rotation (-25° to +25°, plus vertical accents).
3. Strict collision checking with padding (COLLISION_PADDING) prevents illegible text overlap.
4. Hard minimum font size floor (MIN_FONT_SIZE = 9pt) prevents unreadable text mush.
5. Target coverage (70-85%) leaves clean negative space matching professional certificate art.
6. Very dark areas (tie / deep folds) render solid/near-solid dark fill.
7. Dual-tone color system (Navy primary + Gold accent).
"""
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional
from src.art_engine.art_config import (
    MIN_FONT_SIZE, MAX_FONT_SIZE, FILL_RATIO_TARGET_MIN, FILL_RATIO_TARGET_MAX,
    COLLISION_PADDING, ROTATION_CLAMP_MIN, ROTATION_CLAMP_MAX, VERTICAL_TEXT_PROB,
    DARK_AREA_THRESHOLD, PRIMARY_COLOR, ACCENT_COLOR, ACCENT_PERCENTAGE, FONT_PATHS
)


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads system TrueType font or fallback."""
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def render_rotated_word(
    phrase: str,
    font: ImageFont.FreeTypeFont,
    color: Tuple[int, int, int, int],
    angle_deg: float
) -> Tuple[Image.Image, np.ndarray]:
    """
    Renders text onto a transparent RGBA PIL image and rotates it by angle_deg.
    Returns (rotated_pil_img, alpha_mask_np).
    """
    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), phrase, font=font)
    tw = max(1, bbox[2] - bbox[0] + 4)
    th = max(1, bbox[3] - bbox[1] + 4)

    txt_img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    t_draw = ImageDraw.Draw(txt_img)
    t_draw.text((2 - bbox[0], 2 - bbox[1]), phrase, fill=color, font=font)

    if abs(angle_deg) > 0.5:
        rotated = txt_img.rotate(angle_deg, expand=True, resample=Image.Resampling.BICUBIC)
    else:
        rotated = txt_img

    alpha_mask = np.array(rotated)[:, :, 3] > 20
    return rotated, alpha_mask


def render_word_art_portrait(
    mask_np: np.ndarray,
    density_map: np.ndarray,
    text_pool: List[Tuple[str, int]],
    grad_x: Optional[np.ndarray] = None,
    grad_y: Optional[np.ndarray] = None,
    output_size: Tuple[int, int] = (1600, 1600),
) -> Image.Image:
    """
    Renders word art inside clothing_mask with shading-driven sizing, flow rotation,
    collision checking, and target ink coverage (70-85%).
    """
    canvas_w, canvas_h = output_size

    # Resize input arrays to target output canvas
    pil_mask = Image.fromarray(mask_np).resize(output_size, Image.Resampling.BILINEAR)
    resized_mask = np.array(pil_mask) > 100

    pil_shading = Image.fromarray((density_map * 255).astype(np.uint8)).resize(output_size, Image.Resampling.BILINEAR)
    shading_grid = np.array(pil_shading).astype(np.float32) / 255.0

    if grad_x is not None and grad_y is not None:
        pil_gx = Image.fromarray(grad_x).resize(output_size, Image.Resampling.BILINEAR)
        pil_gy = Image.fromarray(grad_y).resize(output_size, Image.Resampling.BILINEAR)
        gx_grid = np.array(pil_gx)
        gy_grid = np.array(pil_gy)
    else:
        gx_grid = np.zeros((canvas_h, canvas_w), dtype=np.float32)
        gy_grid = np.zeros((canvas_h, canvas_w), dtype=np.float32)

    # 1. Prepare Base Canvas & Occupancy Map
    canvas = Image.new("RGBA", output_size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)
    occupied = np.zeros((canvas_h, canvas_w), dtype=bool)

    total_clothing_px = np.count_nonzero(resized_mask)
    if total_clothing_px == 0:
        return canvas

    target_max_filled = int(total_clothing_px * FILL_RATIO_TARGET_MAX)

    # 2. Render Deep Shadow & Tie Fills (Where shading > DARK_AREA_THRESHOLD)
    dark_mask = np.logical_and(resized_mask, shading_grid > DARK_AREA_THRESHOLD)
    if np.any(dark_mask):
        dark_rgba = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
        dark_rgba[dark_mask, 0] = PRIMARY_COLOR[0]
        dark_rgba[dark_mask, 1] = PRIMARY_COLOR[1]
        dark_rgba[dark_mask, 2] = PRIMARY_COLOR[2]
        dark_rgba[dark_mask, 3] = 230
        dark_pil = Image.fromarray(dark_rgba, mode="RGBA")
        canvas = Image.alpha_composite(canvas, dark_pil)
        occupied[dark_mask] = True

    # 3. Categorize & Sort Text Pool
    high_priority = [phrase for phrase, w in text_pool if w >= 4]
    medium_priority = [phrase for phrase, w in text_pool if 2 <= w < 4]
    low_priority = [phrase for phrase, _ in text_pool]

    if not high_priority:
        high_priority = low_priority
    if not medium_priority:
        medium_priority = low_priority

    # 4. Collect Available Placement Coordinates inside Clothing Mask
    valid_grid = (resized_mask & ~occupied)
    sample_step = 12
    sub_y, sub_x = np.where(valid_grid[::sample_step, ::sample_step])
    if len(sub_y) == 0:
        return canvas

    points = [(int(x * sample_step), int(y * sample_step)) for x, y in zip(sub_x, sub_y)]
    random.seed(42)
    random.shuffle(points)

    # Sort candidates by shading density (darker shadow areas first)
    points.sort(key=lambda pt: shading_grid[pt[1], pt[0]], reverse=True)

    filled_pixels = np.count_nonzero(occupied & resized_mask)

    # 5. Iterative Word Placement
    for i in range(len(points)):


        if filled_pixels >= target_max_filled:
            break

        x, y = points[i]
        if occupied[y, x]:
            continue

        dens = shading_grid[y, x]

        # Calculate font size from shading density: darker = smaller/denser, lighter = larger
        font_size = int(MIN_FONT_SIZE + (1.0 - dens) * (MAX_FONT_SIZE - MIN_FONT_SIZE))
        font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, font_size))

        font = get_font(font_size)

        # Select phrase based on density and importance
        is_accent = random.random() < ACCENT_PERCENTAGE
        if is_accent and high_priority:
            phrase = random.choice(high_priority)
            color_rgb = ACCENT_COLOR
        elif dens > 0.4:
            phrase = random.choice(high_priority if random.random() < 0.6 else medium_priority)
            color_rgb = PRIMARY_COLOR
        else:
            phrase = random.choice(low_priority)
            color_rgb = (PRIMARY_COLOR[0] + 15, PRIMARY_COLOR[1] + 15, PRIMARY_COLOR[2] + 20)

        # Determine rotation from local Sobel gradient direction
        gx_val = gx_grid[y, x]
        gy_val = gy_grid[y, x]
        angle_deg = np.arctan2(gy_val, gx_val) * 180.0 / np.pi

        # Clamp angle or apply vertical accent
        if random.random() < VERTICAL_TEXT_PROB:
            angle_deg = 90.0 if random.random() < 0.5 else -90.0
        else:
            angle_deg = np.clip(angle_deg, ROTATION_CLAMP_MIN, ROTATION_CLAMP_MAX)

        # Render rotated word tile
        word_img, alpha_mask = render_rotated_word(phrase, font, color_rgb + (255,), angle_deg)
        w_h, w_w = alpha_mask.shape

        # Center tile at (x, y)
        x1 = x - w_w // 2
        y1 = y - w_h // 2
        x2 = x1 + w_w
        y2 = y1 + w_h

        # Bounds check
        if x1 < 0 or y1 < 0 or x2 > canvas_w or y2 > canvas_h:
            continue

        # Check collision with existing words + padding
        pad = COLLISION_PADDING
        px1 = max(0, x1 - pad)
        py1 = max(0, y1 - pad)
        px2 = min(canvas_w, x2 + pad)
        py2 = min(canvas_h, y2 + pad)

        if np.any(occupied[py1:py2, px1:px2]):
            continue

        # Ensure word fits inside clothing mask
        mask_region = resized_mask[y1:y2, x1:x2]
        if np.count_nonzero(mask_region & alpha_mask) < np.count_nonzero(alpha_mask) * 0.85:
            continue

        # Paste word onto canvas
        canvas.paste(word_img, (x1, y1), word_img)
        occupied[y1:y2, x1:x2] = np.logical_or(occupied[y1:y2, x1:x2], alpha_mask)

        filled_pixels += np.count_nonzero(alpha_mask)

    return canvas
