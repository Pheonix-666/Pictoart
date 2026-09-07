"""
density.py — Shading density map and Sobel gradient field for PICTOART renderer.

Public API (matched to call sites in jobs.py and test_core.py):

    create_density_map(gray_np, mask) -> np.ndarray   [float32, 0..1]
        Called by: test_core.py (TestDensityMap)

    create_shading_and_gradient_map(gray_np, clothing_mask)
        -> (shading_map, grad_x, grad_y)
        Called by: jobs.py (process_doctor_art_job)

The density map encodes "how dark is this pixel relative to the rest of the
clothing region" — high value = pack more / larger words there.
The gradient field encodes local edge direction — used by renderer.py to
rotate words so they follow fabric contours (lapel creases, shoulder seams).
"""
import cv2
import numpy as np


# ── Public: density map ──────────────────────────────────────────────────────

def create_density_map(gray_np: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Returns a float32 density map, same shape as gray_np, values in [0, 1].

    Higher value = darker original pixel = should receive MORE / LARGER words.

    Algorithm
    ---------
    1. Invert grayscale  →  dark pixels become high-density candidates.
    2. Normalize [0, 1] using min-max computed *only over pixels inside mask*
       so a mostly-light blazer doesn't wash out to near-zero everywhere.
    3. Light Gaussian blur (σ = 6) for smooth density transitions instead of
       per-pixel jumps that produce scattered word sizes.
    4. Zero everything outside mask (background pixels stay 0.0).
    5. Degenerate guard: if the masked region is uniform (max == min), return
       constant 0.5 instead of dividing by zero.
    """
    if gray_np.ndim != 2:
        raise ValueError(f"gray_np must be 2-D, got shape {gray_np.shape}")
    if mask.shape != gray_np.shape:
        raise ValueError(
            f"mask shape {mask.shape} does not match gray_np shape {gray_np.shape}"
        )

    mask_bool = mask > 0

    # Early-exit: empty mask → all zeros
    if not np.any(mask_bool):
        return np.zeros(gray_np.shape, dtype=np.float32)

    # Step 1 — invert: dark original → high value
    inverted = (255.0 - gray_np.astype(np.float32))

    # Step 2 — min-max normalisation inside mask only
    inside_vals = inverted[mask_bool]
    v_min = float(inside_vals.min())
    v_max = float(inside_vals.max())

    if v_max - v_min < 1.0:
        # Degenerate uniform region — constant mid-density
        normalized = np.where(mask_bool, 0.5, 0.0).astype(np.float32)
    else:
        normalized = (inverted - v_min) / (v_max - v_min)
        normalized = np.clip(normalized, 0.0, 1.0).astype(np.float32)

    # Step 3 — smooth transitions
    smoothed = cv2.GaussianBlur(normalized, (0, 0), sigmaX=6.0, sigmaY=6.0)

    # Step 4 — zero outside mask
    smoothed[~mask_bool] = 0.0

    return smoothed.astype(np.float32)


# ── Public: gradient field ────────────────────────────────────────────────────

def compute_gradient_field(gray_np: np.ndarray) -> tuple:
    """
    Returns (grad_x, grad_y) as float32 Sobel gradient arrays (same shape as
    gray_np).

    The input is pre-smoothed with a small Gaussian (σ=2) to suppress JPEG
    compression artefacts and sensor noise that would otherwise dominate Sobel
    at ksize=5 and produce erratic word rotations.

    Downstream usage in renderer.py::
        angle_deg = degrees(atan2(grad_y[y, x], grad_x[y, x]))
    """
    smoothed = cv2.GaussianBlur(
        gray_np.astype(np.float32), (0, 0), sigmaX=2.0, sigmaY=2.0
    )
    grad_x = cv2.Sobel(smoothed, cv2.CV_32F, 1, 0, ksize=5)
    grad_y = cv2.Sobel(smoothed, cv2.CV_32F, 0, 1, ksize=5)
    return grad_x, grad_y


# ── Public: combined convenience function (jobs.py call site) ─────────────────

def create_shading_and_gradient_map(
    gray_np: np.ndarray,
    clothing_mask: np.ndarray,
) -> tuple:
    """
    Convenience wrapper called by jobs.py::process_doctor_art_job.

    Returns
    -------
    shading_map : np.ndarray  float32  [0, 1]   — word size/density driver
    grad_x      : np.ndarray  float32           — horizontal edge response
    grad_y      : np.ndarray  float32           — vertical edge response
    """
    shading_map = create_density_map(gray_np, clothing_mask)
    grad_x, grad_y = compute_gradient_field(gray_np)
    return shading_map, grad_x, grad_y
