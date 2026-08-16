import io
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Optional
from src.art_engine.renderer import get_font

from src.art_engine.art_config import FACE_FEATHER_RADIUS


def composite_two_region_portrait(
    word_art_body: Image.Image,
    sketch_face: Image.Image,
    face_mask: np.ndarray,
    output_size: Tuple[int, int] = (1600, 1600),
) -> Image.Image:
    """
    Layers sketch_face on top of word_art_body using a wide feathered alpha
    blend at the face boundary.  The blend uses:
    1. A dilation pass so the sketch overflows slightly into the body before
       the gradient starts — eliminating the hard-edge ring.
    2. A wide Gaussian blur (FACE_FEATHER_RADIUS) for a gradual falloff.

    Raises ValueError if face_mask, word_art_body, and sketch_face do not
    resolve to the same pixel dimensions after resize — preventing silent
    misalignment between the two portrait regions.
    """
    ow, oh = output_size  # canvas width, height

    # Resize both images to the canonical output_size
    body_rgba   = word_art_body.convert("RGBA").resize(output_size, Image.Resampling.LANCZOS)
    sketch_rgba = sketch_face.convert("RGBA").resize(output_size, Image.Resampling.LANCZOS)

    # Resize face_mask to output_size
    pil_mask = Image.fromarray(face_mask).resize(output_size, Image.Resampling.BILINEAR)
    mask_np  = np.array(pil_mask)

    # ── Dimension assertion — catch silent misalignments ────────────────────
    body_arr   = np.array(body_rgba)
    sketch_arr = np.array(sketch_rgba)
    if mask_np.shape != (oh, ow):
        raise ValueError(
            f"face_mask resized to {mask_np.shape} but output_size is {output_size}"
        )
    if body_arr.shape[:2] != (oh, ow):
        raise ValueError(
            f"word_art_body is {body_arr.shape[:2]} after resize but output_size is {output_size}"
        )
    if sketch_arr.shape[:2] != (oh, ow):
        raise ValueError(
            f"sketch_face is {sketch_arr.shape[:2]} after resize but output_size is {output_size}"
        )

    # ── Build feathered alpha mask ──────────────────────────────────────────
    # 1. Dilate first: sketch overflows slightly into body before gradient
    dilate_kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
    dilated_mask   = cv2.dilate(mask_np, dilate_kernel)

    # 2. Wide Gaussian blur → soft gradient with no visible ring
    feather_k      = FACE_FEATHER_RADIUS if FACE_FEATHER_RADIUS % 2 == 1 else FACE_FEATHER_RADIUS + 1
    feathered_mask = cv2.GaussianBlur(dilated_mask, (feather_k, feather_k), 0)

    # Combine with existing sketch alpha (respects face_mask + sketch transparency)
    original_alpha = sketch_arr[:, :, 3].astype(np.float32) / 255.0
    feather_alpha  = feathered_mask.astype(np.float32) / 255.0
    final_alpha    = (original_alpha * feather_alpha * 255.0).clip(0, 255).astype(np.uint8)
    sketch_arr[:, :, 3] = final_alpha

    feathered_sketch = Image.fromarray(sketch_arr, mode="RGBA")

    # Alpha composite sketch face over word-art body
    composited = Image.alpha_composite(body_rgba, feathered_sketch)
    return composited


def create_certificate_layout(
    portrait_img: Image.Image,
    doctor_name: str,
    specialization: Optional[str] = None,
    years_experience: Optional[int] = None,
    achievements_text: Optional[str] = None,
    cert_size: Tuple[int, int] = (2400, 3200) # 300 DPI 8x10.6 inch certificate
) -> Image.Image:
    """
    Composes the final print-ready certificate combining branding, borders,
    word-art portrait, and a legible bottom caption block.
    """
    canvas_w, canvas_h = cert_size
    cert = Image.new("RGB", cert_size, (252, 252, 250))
    draw = ImageDraw.Draw(cert)

    # Color Palette
    border_gold = (195, 155, 65)
    navy_blue = (18, 32, 60)
    dark_gray = (60, 64, 72)
    accent_red = (140, 30, 40)

    # Decorative Border
    border_margin = 80
    border_thickness = 12
    draw.rectangle(
        [border_margin, border_margin, canvas_w - border_margin, canvas_h - border_margin],
        outline=border_gold,
        width=border_thickness
    )
    # Inner thin border
    inner_margin = border_margin + 20
    draw.rectangle(
        [inner_margin, inner_margin, canvas_w - inner_margin, canvas_h - inner_margin],
        outline=navy_blue,
        width=3
    )

    # Corner ornaments
    corner_size = 40
    for cx, cy in [
        (border_margin, border_margin),
        (canvas_w - border_margin, border_margin),
        (border_margin, canvas_h - border_margin),
        (canvas_w - border_margin, canvas_h - border_margin)
    ]:
        draw.rectangle([cx - corner_size//2, cy - corner_size//2, cx + corner_size//2, cy + corner_size//2], fill=border_gold)

    # Header Title
    title_font = get_font(68)
    subtitle_font = get_font(36)

    title_text = "DOCTOR OF EXCELLENCE"
    bbox = draw.textbbox((0, 0), title_text, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((canvas_w - tw) // 2, 160), title_text, fill=navy_blue, font=title_font)

    sub_text = "HONORARY SKETCH PORTRAIT CERTIFICATE"
    bbox_sub = draw.textbbox((0, 0), sub_text, font=subtitle_font)
    sw = bbox_sub[2] - bbox_sub[0]
    draw.text(((canvas_w - sw) // 2, 245), sub_text, fill=border_gold, font=subtitle_font)

    # Decorative dividing line
    draw.line([(canvas_w // 2 - 300, 310), (canvas_w // 2 + 300, 310)], fill=border_gold, width=3)

    # Center Word-Art Portrait
    portrait_target_size = (1500, 1500)
    resized_portrait = portrait_img.resize(portrait_target_size, Image.Resampling.LANCZOS)
    
    portrait_x = (canvas_w - portrait_target_size[0]) // 2
    portrait_y = 350

    # Paste portrait with transparency
    if resized_portrait.mode == "RGBA":
        cert.paste(resized_portrait, (portrait_x, portrait_y), resized_portrait)
    else:
        cert.paste(resized_portrait, (portrait_x, portrait_y))

    # Caption Section below Portrait
    caption_y = portrait_y + portrait_target_size[1] + 60

    # Doctor Name
    name_str = doctor_name.strip()
    if not name_str.lower().startswith("dr.") and not name_str.lower().startswith("dr "):
        name_str = f"Dr. {name_str}"

    name_font = get_font(84)
    bbox_name = draw.textbbox((0, 0), name_str, font=name_font)
    nw = bbox_name[2] - bbox_name[0]
    draw.text(((canvas_w - nw) // 2, caption_y), name_str, fill=navy_blue, font=name_font)

    curr_y = caption_y + 110

    # Specialization & Experience Line
    details_parts = []
    if specialization:
        details_parts.append(specialization.strip())
    if years_experience:
        details_parts.append(f"{years_experience}+ Years of Medical Practice")

    if details_parts:
        details_str = "  •  ".join(details_parts)
        spec_font = get_font(42)
        bbox_spec = draw.textbbox((0, 0), details_str, font=spec_font)
        spw = bbox_spec[2] - bbox_spec[0]
        draw.text(((canvas_w - spw) // 2, curr_y), details_str, fill=border_gold, font=spec_font)
        curr_y += 65

    # Achievements excerpt line
    if achievements_text:
        achieve_str = f'"{achievements_text.strip()[:140]}"'
        ach_font = get_font(34)
        bbox_ach = draw.textbbox((0, 0), achieve_str, font=ach_font)
        aw = bbox_ach[2] - bbox_ach[0]
        if aw > canvas_w - 300:
            achieve_str = achieve_str[:90] + '..."'
            bbox_ach = draw.textbbox((0, 0), achieve_str, font=ach_font)
            aw = bbox_ach[2] - bbox_ach[0]
        draw.text(((canvas_w - aw) // 2, curr_y), achieve_str, fill=dark_gray, font=ach_font)
        curr_y += 80

    # Footer Branding & Seals
    draw.line([(border_margin + 100, canvas_h - 220), (canvas_w - border_margin - 100, canvas_h - 220)], fill=(220, 220, 220), width=2)

    footer_font = get_font(28)
    draw.text((border_margin + 100, canvas_h - 180), "PRESENTED WITH GRATITUDE FOR EXEMPLARY SERVICE", fill=dark_gray, font=footer_font)
    draw.text((canvas_w - border_margin - 550, canvas_h - 180), "AUTHENTICATED CERTIFICATE", fill=dark_gray, font=footer_font)

    return cert

def export_print_ready_certificate(cert_img: Image.Image, output_path: str, format: str = "PNG"):
    """
    Saves high-res certificate image at 300 DPI.
    Supports PNG and PDF formats.
    """
    if format.upper() == "PDF":
        pdf_img = cert_img.convert("RGB")
        pdf_img.save(output_path, "PDF", resolution=300.0)
    else:
        cert_img.save(output_path, "PNG", dpi=(300, 300))
