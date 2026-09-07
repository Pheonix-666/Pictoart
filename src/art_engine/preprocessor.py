import io
import cv2
import numpy as np
from PIL import Image
from src.config import settings

def validate_photo_quality(image_bytes: bytes) -> tuple[bool, str, bool, tuple[int, int]]:
    """
    Validates photo resolution, file readability, and checks for basic quality.
    Returns: (is_valid, error_message, face_detected, (width, height))
    """
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img.verify()
    except Exception as e:
        return False, f"Invalid or corrupted image file: {str(e)}", False, (0, 0)

    # Re-open after verify()
    pil_img = Image.open(io.BytesIO(image_bytes))
    width, height = pil_img.size
    min_w, min_h = settings.MIN_IMAGE_RESOLUTION

    if width < min_w or height < min_h:
        return False, f"Photo resolution ({width}x{height}) is lower than minimum recommended ({min_w}x{min_h}px).", False, (width, height)

    # Convert to OpenCV format to check face detection
    img_np = np.array(pil_img.convert("RGB"))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    # OpenCV Haar Cascade face detector (only if CascadeClassifier is available)
    if not hasattr(cv2, 'CascadeClassifier'):
        return True, "", False, (width, height)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))

    face_detected = len(faces) > 0

    return True, "", face_detected, (width, height)

def preprocess_image(image_bytes: bytes, target_size: tuple[int, int] = (1200, 1200)) -> tuple[np.ndarray, np.ndarray, Image.Image]:
    """
    Loads, normalizes, and resizes the photo.
    Returns: (gray_np, color_np, resized_pil_img)
    """
    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
    # Aspect ratio preserving resize or crop to target_size
    img_w, img_h = pil_img.size
    target_w, target_h = target_size
    
    # Center crop to target aspect ratio
    target_aspect = target_w / target_h
    img_aspect = img_w / img_h
    
    if img_aspect > target_aspect:
        # Image is wider
        new_w = int(img_h * target_aspect)
        left = (img_w - new_w) // 2
        pil_img = pil_img.crop((left, 0, left + new_w, img_h))
    else:
        # Image is taller
        new_h = int(img_w / target_aspect)
        top = (img_h - new_h) // 2
        pil_img = pil_img.crop((0, top, img_w, top + new_h))

    pil_img = pil_img.resize(target_size, Image.Resampling.LANCZOS)
    
    color_np = np.array(pil_img)
    gray_np = cv2.cvtColor(color_np, cv2.COLOR_RGB2GRAY)

    # CLAHE: adaptive local contrast — far less blocky than equalizeHist
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_np = clahe.apply(gray_np)

    # Unsharp mask: recover edge crispness lost during LANCZOS resize
    blur = cv2.GaussianBlur(gray_np, (0, 0), sigmaX=1.5)
    gray_np = cv2.addWeighted(gray_np, 1.4, blur, -0.4, 0)

    return gray_np, color_np, pil_img
