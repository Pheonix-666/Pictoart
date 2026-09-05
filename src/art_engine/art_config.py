"""
art_config.py — Central configuration for PICTOART Sketch Portrait generation.

Exposes all tunable parameters for pencil sketch rendering, line work, shading,
tonal depth, and composition.
"""
from typing import Tuple

# ── Canvas & Resolution ────────────────────────────────────────────────────
OUTPUT_PORTRAIT_SIZE: Tuple[int, int] = (1600, 1600)  # High-res square canvas for sketch portrait
OUTPUT_CERT_SIZE: Tuple[int, int]     = (2400, 3200)  # 300 DPI 8x10.6 inch presentation layout

# ── Pencil Sketch Line-Art (Contour & Feature Extraction) ──────────────────
LINE_BLUR_KERNEL: int = 5             # Bilateral pre-smoothing to prevent skin noise in lines
DOG_SIGMA1: float = 0.8               # Difference of Gaussians fine sigma
DOG_SIGMA2: float = 1.6               # Difference of Gaussians coarse sigma
DOG_THRESHOLD: float = 0.05           # Sensitivity of pencil stroke edge detection
PENCIL_LINE_WEIGHT: float = 0.45       # Weight of sharp pencil contours in final sketch

# ── Tonal Graphite Shading & Soft Dodge ────────────────────────────────────
SKETCH_BLUR_KERNEL: int = 15          # Gaussian blur kernel for Color Dodge pencil shading (must be odd)
SKETCH_GAMMA: float = 1.25            # Gamma adjustment (< 1.0 lighter, > 1.0 richer dark graphite tones)
DODGE_WEIGHT: float = 0.60            # Balance of color dodge pencil highlights vs natural tone
TONAL_WEIGHT: float = 0.40            # Natural shadow and feature preservation

# ── Subject Masking & Boundary Fade ────────────────────────────────────────
SILHOUETTE_FEATHER_PX: int = 15       # Soft edge feathering around the subject outline
BOUNDARY_DARK_WEIGHT: float = 0.25    # Subtle pencil outline around outer silhouette
NATURAL_OVERLAP_ERODE: int = 21        # Erode kernel size for mask boundary overlap

# ── Paper Texture & Presentation ──────────────────────────────────────────
PAPER_COLOR: Tuple[int, int, int] = (252, 252, 250)   # Warm fine-art sketch paper tone
GRAPHITE_TINT: Tuple[int, int, int] = (30, 30, 34)    # Natural charcoal/graphite dark tone
