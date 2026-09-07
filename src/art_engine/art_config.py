"""
art_config.py — Central configuration for PICTOART rendering & segmentation.

Exposes all tunable parameters as named constants and loads the rule-governed
engine settings from `art_rules.json`.
"""
import os
import json
from typing import Tuple, List, Dict, Any

# ── Load Rule-Governed Settings from art_rules.json ──────────────────────────
_RULES_PATH = os.path.join(os.path.dirname(__file__), "art_rules.json")

def load_art_rules() -> Dict[str, Any]:
    """Loads art conversion rules from art_rules.json with fallback defaults."""
    if os.path.exists(_RULES_PATH):
        try:
            with open(_RULES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[art_config] Warning: Failed to parse art_rules.json ({e}), using defaults.")
    
    # Built-in fallback rule defaults
    return {
        "version": "2.0.0",
        "canvas": {"default_width": 2048, "default_height": 2048, "background_mode": "transparent", "dpi": 300},
        "segmentation": {
            "neck_v_aspect_ratio": 0.65,
            "neck_v_dilation_px": 28,
            "skin_ycrcb": {"cb_min": 77, "cb_max": 127, "cr_min": 133, "cr_max": 173},
            "skin_hsv": {"h_min": 0, "h_max": 25, "s_min": 25, "s_max": 175}
        },
        "hatching": {
            "angles_deg": [-35.0, 52.0, -75.0, 15.0],
            "line_spacing_px": 4,
            "line_thickness_px": 1,
            "tone_cutoffs": {"light": [0.65, 0.82], "mid": [0.40, 0.65], "shadow": [0.18, 0.40], "deep_dark": 0.18},
            "edge_preservation": {"canny_low": 28, "canny_high": 92, "dog_kernel_1": 3, "dog_kernel_2": 7, "dog_threshold": 5},
            "graphite_texture": {"dodge_weight": 0.28, "hatch_weight": 0.72, "paper_tooth_noise": 0.05}
        },
        "typography": {
            "font_hierarchy": [
                {"tier": "headline", "font_size": 28, "step_y": 26, "step_x": 16, "min_occupancy": 0.80, "vertical_prob": 0.12, "max_overlap": 0.20},
                {"tier": "subheading", "font_size": 18, "step_y": 16, "step_x": 12, "min_occupancy": 0.76, "vertical_prob": 0.22, "max_overlap": 0.30},
                {"tier": "body", "font_size": 12, "step_y": 11, "step_x": 8, "min_occupancy": 0.70, "vertical_prob": 0.32, "max_overlap": 0.45},
                {"tier": "fine", "font_size": 8, "step_y": 7, "step_x": 5, "min_occupancy": 0.62, "vertical_prob": 0.38, "max_overlap": 0.50}
            ],
            "tone_inversion": {
                "shading_density_cutoff": 0.60,
                "collar_proximity_px": 55,
                "collar_depth_px": 260,
                "inverted_block_threshold": 0.35,
                "box_fill_rgba": [18, 18, 18, 255],
                "text_inverted_rgba": [255, 255, 255, 255],
                "text_standard_rgba": [15, 15, 15, 255]
            },
            "garment_seams": {
                "blur_ksize": 13,
                "canny_low": 50,
                "canny_high": 140,
                "min_component_area": 35,
                "line_rgba": [15, 15, 15, 255]
            }
        },
        "composite": {
            "feather_radius": 91,
            "dilation_kernel_size": 31
        }
    }

ART_RULES: Dict[str, Any] = load_art_rules()

# ── Canvas & Resolution ────────────────────────────────────────────────────
OUTPUT_PORTRAIT_SIZE: Tuple[int, int] = (
    ART_RULES.get("canvas", {}).get("default_width", 2048),
    ART_RULES.get("canvas", {}).get("default_height", 2048)
)
OUTPUT_CERT_SIZE: Tuple[int, int]     = (2400, 3200)  # 300 DPI 8x10.6 inch certificate

# ── Segmentation & Masking ──────────────────────────────────────────────────
FACE_FEATHER_RADIUS: int = ART_RULES.get("composite", {}).get("feather_radius", 91)
NATURAL_OVERLAP_ERODE: int = 21        # Erode kernel size for natural mask boundary overlap

# ── Word Art Density & Coverage ─────────────────────────────────────────────
FILL_RATIO_TARGET_MIN: float = 0.70    # Target minimum ink coverage (70%)
FILL_RATIO_TARGET_MAX: float = 0.85    # Target maximum ink coverage (85%)
COLLISION_PADDING: int = 3             # Required padding (px) between placed word bounding boxes

# ── Font Size & Scaling ─────────────────────────────────────────────────────
MIN_FONT_SIZE: int = 8                 # Hard floor font size (pt)
MAX_FONT_SIZE: int = 38                # Maximum font size (pt) for highlight areas

# ── Rotation & Flow ─────────────────────────────────────────────────────────
ROTATION_CLAMP_MIN: float = -15.0      # Minimum rotation angle (deg) along gradient flow
ROTATION_CLAMP_MAX: float = 15.0       # Maximum rotation angle (deg) along gradient flow
VERTICAL_TEXT_PROB: float = 0.20       # Probability of 90-deg vertical text matching reference suit lapel style

# ── Dark Areas & Deep Shadows ───────────────────────────────────────────────
DARK_AREA_THRESHOLD: float = 0.96      # Shading threshold for solid fill

# ── Color Palette & Accents ─────────────────────────────────────────────────
PRIMARY_COLOR: Tuple[int, int, int] = (15, 15, 15)      # Deep Charcoal text
ACCENT_COLOR: Tuple[int, int, int]  = (20, 20, 25)      # Charcoal accent
ACCENT_PERCENTAGE: float = 0.05                         # Accent ratio

# ── Sketch Face Parameters ──────────────────────────────────────────────────
SKETCH_BLUR_KERNEL: int = 21           # Sized for 1600 px canvas — wider kernel = richer dodge effect
SKETCH_GAMMA: float = 1.35             # Gamma curve

# ── Typography Fonts ────────────────────────────────────────────────────────
FONT_PATHS: List[str] = [
    "C:\\Windows\\Fonts\\impact.ttf",
    "C:\\Windows\\Fonts\\ariblk.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\georgiab.ttf",
    "C:\\Windows\\Fonts\\tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc"
]
