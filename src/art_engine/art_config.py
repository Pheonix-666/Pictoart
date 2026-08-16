"""
art_config.py — Central configuration for PICTOART rendering & segmentation.

Exposes all tunable parameters as named constants. No magic numbers buried in code.
"""
from typing import Tuple, List

# ── Canvas & Resolution ────────────────────────────────────────────────────
OUTPUT_PORTRAIT_SIZE: Tuple[int, int] = (1600, 1600)  # Canvas for word art + face sketch
OUTPUT_CERT_SIZE: Tuple[int, int]     = (2400, 3200)  # 300 DPI 8x10.6 inch certificate

# ── Segmentation & Masking ──────────────────────────────────────────────────
FACE_FEATHER_RADIUS: int = 91          # Gaussian blur radius for face/body transition seam (must be odd)
NATURAL_OVERLAP_ERODE: int = 21        # Erode kernel size for natural mask boundary overlap

# ── Word Art Density & Coverage ─────────────────────────────────────────────
FILL_RATIO_TARGET_MIN: float = 0.70    # Target minimum ink coverage (70%)
FILL_RATIO_TARGET_MAX: float = 0.85    # Target maximum ink coverage (85%)
COLLISION_PADDING: int = 3             # Required padding (px) between placed word bounding boxes

# ── Font Size & Scaling ─────────────────────────────────────────────────────
MIN_FONT_SIZE: int = 9                 # Hard floor font size (pt) at 1600x1600 canvas
MAX_FONT_SIZE: int = 38                # Maximum font size (pt) for highlight areas

# ── Rotation & Flow ─────────────────────────────────────────────────────────
ROTATION_CLAMP_MIN: float = -25.0      # Minimum rotation angle (deg) along gradient flow
ROTATION_CLAMP_MAX: float = 25.0       # Maximum rotation angle (deg) along gradient flow
VERTICAL_TEXT_PROB: float = 0.08       # Probability of 90-deg vertical text along side seams/lapels

# ── Dark Areas & Deep Shadows ───────────────────────────────────────────────
DARK_AREA_THRESHOLD: float = 0.82      # Shading threshold (0.0 - 1.0) for solid fill / deep shadow folds

# ── Color Palette & Accents ─────────────────────────────────────────────────
PRIMARY_COLOR: Tuple[int, int, int] = (15, 25, 45)      # Deep Navy / Charcoal (~90-95% of words)
ACCENT_COLOR: Tuple[int, int, int]  = (195, 155, 65)    # Gold / Amber (~5-10% of high-priority words)
ACCENT_PERCENTAGE: float = 0.08                         # Fraction of words using accent color

# ── Sketch Face Parameters ──────────────────────────────────────────────────
SKETCH_BLUR_KERNEL: int = 9            # Smaller kernel = finer detail lines (eyes, hair, features)
SKETCH_GAMMA: float = 1.35             # Gamma curve > 1.0 makes sketch darker and more detailed


# ── Typography ──────────────────────────────────────────────────────────────
FONT_PATHS: List[str] = [
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\georgiab.ttf",
    "C:\\Windows\\Fonts\\tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc"
]
