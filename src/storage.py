import os
import shutil
from typing import Union
from PIL import Image
from src.config import settings

class StorageManager:
    def __init__(self, base_dir: str = settings.STORAGE_DIR):
        self.base_dir = os.path.abspath(base_dir)
        self.originals_dir = os.path.join(self.base_dir, "originals")
        self.generated_dir = os.path.join(self.base_dir, "generated")
        self.exports_dir = os.path.join(self.base_dir, "exports")

        os.makedirs(self.originals_dir, exist_ok=True)
        os.makedirs(self.generated_dir, exist_ok=True)
        os.makedirs(self.exports_dir, exist_ok=True)

    def save_original_photo(self, file_bytes: bytes, doctor_id: int, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"
        target_filename = f"doctor_{doctor_id}_orig{ext}"
        target_path = os.path.join(self.originals_dir, target_filename)
        
        with open(target_path, "wb") as f:
            f.write(file_bytes)
            
        return os.path.join("originals", target_filename)

    def save_generated_art(self, image: Image.Image, doctor_id: int, format: str = "PNG") -> str:
        ext = f".{format.lower()}"
        target_filename = f"doctor_{doctor_id}_art{ext}"
        target_path = os.path.join(self.generated_dir, target_filename)
        
        image.save(target_path, format=format, dpi=(300, 300))
        return os.path.join("generated", target_filename)

    def get_full_path(self, path_or_filename: str) -> str:
        if not path_or_filename:
            return ""
        if os.path.isabs(path_or_filename):
            return path_or_filename
            
        # Check if already prefixed with storage dir
        norm_path = os.path.normpath(path_or_filename)
        if norm_path.startswith(self.base_dir):
            return norm_path
            
        return os.path.join(self.base_dir, norm_path)

    def delete_doctor_files(self, doctor_id: int):
        for folder in [self.originals_dir, self.generated_dir]:
            if os.path.exists(folder):
                for fname in os.listdir(folder):
                    if fname.startswith(f"doctor_{doctor_id}_"):
                        try:
                            os.remove(os.path.join(folder, fname))
                        except Exception:
                            pass

storage = StorageManager()
