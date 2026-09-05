"""
composer.py — Layout composition & export for PICTOART Sketch Portraits.

Composes the generated graphite pencil portrait into a print-ready presentation
with elegant borders, typography, and captions at 300 DPI.
"""
from typing import Tuple, Optional, List
from PIL import Image, ImageDraw, ImageFont
from src.art_engine.art_config import PAPER_COLOR

FONT_PATHS: List[str] = [
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\georgiab.ttf",
    "C:\\Windows\\Fonts\\georgia.ttf",
    "C:\\Windows\\Fonts\\tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads a TrueType font from standard system paths with default fallback."""
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def create_certificate_layout(
    portrait_img: Image.Image,
    doctor_name: str,
    specialization: Optional[str] = None,
    years_experience: Optional[int] = None,
    achievements_text: Optional[str] = None,
    cert_size: Tuple[int, int] = (2400, 3200)  # 300 DPI 8x10.6 inch certificate
) -> Image.Image:
    """
    Composes the final print-ready certificate combining classical borders,
    the artistic pencil sketch portrait, and an elegant caption block.
    """
    canvas_w, canvas_h = cert_size
    cert = Image.new("RGB", cert_size, PAPER_COLOR)
    draw = ImageDraw.Draw(cert)

    # Color Palette
    border_gold = (195, 155, 65)
    navy_blue = (18, 32, 60)
    dark_gray = (60, 64, 72)

    # Outer Decorative Border
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
        draw.rectangle(
            [cx - corner_size // 2, cy - corner_size // 2, cx + corner_size // 2, cy + corner_size // 2],
            fill=border_gold
        )

    # Header Title
    title_font = get_font(68)
    subtitle_font = get_font(36)

    title_text = "DOCTOR OF EXCELLENCE"
    bbox = draw.textbbox((0, 0), title_text, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((canvas_w - tw) // 2, 160), title_text, fill=navy_blue, font=title_font)

    sub_text = "HONORARY PENCIL SKETCH PORTRAIT"
    bbox_sub = draw.textbbox((0, 0), sub_text, font=subtitle_font)
    sw = bbox_sub[2] - bbox_sub[0]
    draw.text(((canvas_w - sw) // 2, 245), sub_text, fill=border_gold, font=subtitle_font)

    # Decorative dividing line
    draw.line([(canvas_w // 2 - 300, 310), (canvas_w // 2 + 300, 310)], fill=border_gold, width=3)

    # Center Pencil Sketch Portrait
    portrait_target_size = (1500, 1500)
    resized_portrait = portrait_img.resize(portrait_target_size, Image.Resampling.LANCZOS)

    portrait_x = (canvas_w - portrait_target_size[0]) // 2
    portrait_y = 350

    # Paste portrait with transparency if RGBA
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
        details_parts.append(f"{years_experience}+ Years of Dedicated Practice")

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

    # Footer Branding
    draw.line(
        [(border_margin + 100, canvas_h - 220), (canvas_w - border_margin - 100, canvas_h - 220)],
        fill=(220, 220, 220),
        width=2
    )

    footer_font = get_font(28)
    draw.text(
        (border_margin + 100, canvas_h - 180),
        "PRESENTED WITH GRATITUDE FOR EXEMPLARY SERVICE",
        fill=dark_gray,
        font=footer_font
    )
    draw.text(
        (canvas_w - border_margin - 550, canvas_h - 180),
        "AUTHENTICATED SKETCH ART",
        fill=dark_gray,
        font=footer_font
    )

    return cert


def export_print_ready_certificate(cert_img: Image.Image, output_path: str, format: str = "PNG"):
    """
    Saves high-res certificate image at 300 DPI. Supports PNG and PDF formats.
    """
    if format.upper() == "PDF":
        pdf_img = cert_img.convert("RGB")
        pdf_img.save(output_path, "PDF", resolution=300.0)
    else:
        cert_img.save(output_path, "PNG", dpi=(300, 300))
