"""
benchmark_samples.py — Validates and benchmarks the calibrated art engine against doctor photos.
Produces isolated transparent PNG portraits (no certificates).
"""
import os
import time
import numpy as np
from PIL import Image

from src.art_engine.preprocessor import preprocess_image
from src.art_engine.segmentation import extract_masks
from src.art_engine.density import create_shading_and_gradient_map
from src.art_engine.text_pool import build_text_pool
from src.art_engine.renderer import render_word_art_portrait
from src.art_engine.sketch import render_pencil_sketch
from src.art_engine.composer import composite_two_region_portrait
from src.art_engine.art_config import OUTPUT_PORTRAIT_SIZE, ART_RULES

def run_calibration_test(photo_path: str, output_path: str, doctor_name: str = "Dr. Rajesh Kumar"):
    print(f"\n=======================================================")
    print(f"Benchmarking: {photo_path}")
    print(f"Rules Version: {ART_RULES.get('version')} ({ART_RULES.get('name')})")
    print(f"Target Resolution: {OUTPUT_PORTRAIT_SIZE}")
    print(f"=======================================================")

    t0 = time.time()

    with open(photo_path, "rb") as f:
        photo_bytes = f.read()

    # Step 1: Preprocessing
    t_step = time.time()
    gray_np, color_np, resized_pil = preprocess_image(photo_bytes, target_size=(1200, 1200))
    print(f"[1/6] Preprocessing: {time.time() - t_step:.2f}s (Gray shape: {gray_np.shape})")

    # Step 2: Segmentation
    t_step = time.time()
    sil_mask, nat_mask, cloth_mask = extract_masks(gray_np, color_np)
    print(f"[2/6] Segmentation: {time.time() - t_step:.2f}s (Nat px: {np.count_nonzero(nat_mask)}, Cloth px: {np.count_nonzero(cloth_mask)})")

    # Step 3: Shading & Gradient
    t_step = time.time()
    density_map, gx, gy = create_shading_and_gradient_map(gray_np, cloth_mask)
    print(f"[3/6] Shading & Gradients: {time.time() - t_step:.2f}s")

    # Step 4: Text Pool & Typography Suit
    t_step = time.time()
    pool = build_text_pool(
        name=doctor_name,
        years_experience=22,
        specialization="Cardiology & Electrophysiology",
        achievements_text="Over 12,000 Angioplasties Performed, Fellow of the American College of Cardiology, Best Physician Award 2023, Pioneer in Cardiac Resynchronization"
    )
    word_art_body = render_word_art_portrait(
        mask_np=cloth_mask,
        density_map=density_map,
        text_pool=pool,
        grad_x=gx,
        grad_y=gy,
        output_size=OUTPUT_PORTRAIT_SIZE,
        natural_mask=nat_mask,
        orig_gray=gray_np
    )
    print(f"[4/6] Typography Suit Render: {time.time() - t_step:.2f}s")

    # Step 5: Pencil Sketch Face
    t_step = time.time()
    sketch_face = render_pencil_sketch(
        gray_np=gray_np,
        mask_np=nat_mask,
        output_size=OUTPUT_PORTRAIT_SIZE
    )
    print(f"[5/6] Pencil Sketch Render: {time.time() - t_step:.2f}s")

    # Step 6: Two-Region Composite (Transparent PNG)
    t_step = time.time()
    portrait_rgba = composite_two_region_portrait(
        word_art_body=word_art_body,
        sketch_face=sketch_face,
        face_mask=nat_mask,
        output_size=OUTPUT_PORTRAIT_SIZE
    )
    print(f"[6/6] Two-Region Composite: {time.time() - t_step:.2f}s")

    total_time = time.time() - t0
    print(f"\n>> TOTAL RUNTIME: {total_time:.2f} seconds <<")

    # Verify attributes
    arr = np.array(portrait_rgba)
    assert portrait_rgba.mode == "RGBA", f"Expected RGBA, got {portrait_rgba.mode}"
    assert portrait_rgba.size == OUTPUT_PORTRAIT_SIZE, f"Expected {OUTPUT_PORTRAIT_SIZE}, got {portrait_rgba.size}"

    # Verify transparent background (corners should have alpha=0)
    top_left_alpha = arr[0, 0, 3]
    top_right_alpha = arr[0, -1, 3]
    print(f"Top-Left corner alpha: {top_left_alpha} (0 = Transparent)")
    print(f"Top-Right corner alpha: {top_right_alpha} (0 = Transparent)")

    # Save to disk
    portrait_rgba.save(output_path, format="PNG", dpi=(300, 300))
    print(f"Saved calibrated portrait to: {output_path}")

    return portrait_rgba

if __name__ == "__main__":
    test_photo = "sample_doctor_photo.jpg"
    if not os.path.exists(test_photo):
        test_photo = "storage/originals/doctor_1_orig.jpg"
    
    out_file = "sample_calibrated_portrait.png"
    run_calibration_test(test_photo, out_file)
