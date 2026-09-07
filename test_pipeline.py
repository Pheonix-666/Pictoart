"""E2E pipeline smoke test — run from project root."""
import time
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Find first available doctor photo
for fname in ["doctor_7.jpg", "doctor_8.jpg", "doctor_9.jpg", "doctor_10.jpg", "sample_doctor_photo.jpg"]:
    if os.path.exists(fname):
        photo_path = fname
        break
else:
    print("No doctor photo found in project root")
    sys.exit(1)

print(f"Using photo: {photo_path}")
with open(photo_path, "rb") as f:
    photo_bytes = f.read()

t0 = time.time()

from src.art_engine.preprocessor import preprocess_image, validate_photo_quality
is_valid, err, face_found, res = validate_photo_quality(photo_bytes)
print(f"[1] valid={is_valid} face={face_found} res={res} err='{err}'")
gray_np, color_np, _ = preprocess_image(photo_bytes, target_size=(600, 600))

from src.art_engine.segmentation import extract_masks
sil, nat, cloth = extract_masks(gray_np, color_np)
print(f"[2] cloth_px={np.count_nonzero(cloth):,} nat_px={np.count_nonzero(nat):,} ({time.time()-t0:.1f}s)")

from src.art_engine.density import create_shading_and_gradient_map
shading, gx, gy = create_shading_and_gradient_map(gray_np, cloth)
print(f"[3] density min={shading.min():.3f} max={shading.max():.3f} ({time.time()-t0:.1f}s)")

from src.art_engine.text_pool import build_text_pool
pool = build_text_pool(
    name="Dr. Rajan Mehta",
    specialization="Cardiology",
    years_experience=18,
    achievements_text="10000 Patients Treated, FACC, Gold Medal"
)
print(f"[4] pool={len(pool)} entries, top5={[p for p,_ in pool[:5]]} ({time.time()-t0:.1f}s)")

from src.art_engine.renderer import render_word_art_portrait
word_art = render_word_art_portrait(
    mask_np=cloth, density_map=shading, text_pool=pool,
    grad_x=gx, grad_y=gy, output_size=(600, 600)
)
arr = np.array(word_art)
ink = np.count_nonzero(arr[:, :, 3] > 0)
total = max(np.count_nonzero(cloth), 1)
print(f"[5] WordArt size={word_art.size} ink_coverage={ink/total*100:.1f}% ({time.time()-t0:.1f}s)")

from src.art_engine.sketch import render_pencil_sketch
sketch = render_pencil_sketch(gray_np=gray_np, mask_np=nat, output_size=(600, 600))
print(f"[6] Sketch done ({time.time()-t0:.1f}s)")

from src.art_engine.composer import composite_two_region_portrait, create_certificate_layout
portrait = composite_two_region_portrait(word_art, sketch, nat, output_size=(600, 600))
print(f"[7] Composite done ({time.time()-t0:.1f}s)")

cert = create_certificate_layout(
    portrait_img=portrait, doctor_name="Dr. Rajan Mehta",
    specialization="Cardiology", years_experience=18,
    achievements_text="10000 Patients Treated, FACC Fellow, Gold Medal",
    cert_size=(900, 1200)
)
out = "test_output_pipeline.png"
cert.save(out)
print(f"[8] Certificate saved: {out}  TOTAL={time.time()-t0:.1f}s")
