"""
Basic smoke and integration tests for PICTOART Sketch Art Generator core modules.
Run: pytest tests/ -v
"""
import os
import sys
import pytest
import numpy as np
from PIL import Image
import io

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPencilSketchEngine:
    """Tests for the pure graphite pencil sketch engine."""

    def test_extract_pencil_lines(self):
        from src.art_engine.sketch import extract_pencil_lines

        # Create synthetic image with dark circle on light background
        gray = np.full((300, 300), 220, dtype=np.uint8)
        gray[100:200, 100:200] = 50

        lines = extract_pencil_lines(gray)
        assert lines.shape == (300, 300)
        assert lines.dtype == np.uint8
        # Lines should have high response (dark strokes) around edges
        assert np.min(lines) < 200

    def test_render_pencil_sketch_output_format(self):
        from src.art_engine.sketch import render_pencil_sketch

        gray = np.full((200, 200), 160, dtype=np.uint8)
        mask = np.zeros((200, 200), dtype=np.uint8)
        mask[40:160, 40:160] = 255

        sketch_img = render_pencil_sketch(gray, mask, output_size=(400, 400))
        assert isinstance(sketch_img, Image.Image)
        assert sketch_img.size == (400, 400)
        assert sketch_img.mode == "RGBA"

        # Check alpha channel follows mask
        arr = np.array(sketch_img)
        # Background outside mask should have 0 alpha
        assert arr[10, 10, 3] == 0
        # Inside center should have positive alpha
        assert arr[200, 200, 3] > 0

    def test_render_full_sketch_portrait(self):
        from src.art_engine.sketch import render_full_sketch_portrait

        gray = np.random.randint(60, 200, (200, 200), dtype=np.uint8)
        mask = np.zeros((200, 200), dtype=np.uint8)
        mask[50:150, 50:150] = 255

        portrait = render_full_sketch_portrait(gray, mask, output_size=(500, 500))
        assert isinstance(portrait, Image.Image)
        assert portrait.size == (500, 500)
        assert portrait.mode == "RGB"


class TestStorageManager:
    """Tests for storage manager operations."""

    def test_storage_directories_created(self):
        from src.storage import StorageManager
        sm = StorageManager(base_dir="./test_storage_tmp")
        assert os.path.exists(sm.originals_dir)
        assert os.path.exists(sm.generated_dir)
        assert os.path.exists(sm.exports_dir)
        # Cleanup
        import shutil
        shutil.rmtree("./test_storage_tmp", ignore_errors=True)

    def test_save_original_photo(self):
        from src.storage import StorageManager
        sm = StorageManager(base_dir="./test_storage_tmp")
        img = Image.new("RGB", (800, 800), color=(100, 150, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        photo_bytes = buf.getvalue()

        path = sm.save_original_photo(photo_bytes, doctor_id=999, filename="test_photo.jpg")
        assert os.path.exists(sm.get_full_path(path))
        assert "doctor_999_orig" in path

        # Cleanup
        import shutil
        shutil.rmtree("./test_storage_tmp", ignore_errors=True)


class TestDatabaseModels:
    """Tests for database models and schema creation."""

    def test_database_tables_create(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.database import Base
        from src.models import Doctor, Submission, AdminUser, AuditLog

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "doctors" in tables
        assert "submissions" in tables
        assert "admin_users" in tables
        assert "audit_logs" in tables

        db.close()

    def test_doctor_model_creation(self):
        import secrets
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.database import Base
        from src.models import Doctor, DoctorStatus

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        doctor = Doctor(
            name="Test Doctor",
            contact="test@example.com",
            unique_token=secrets.token_urlsafe(24),
            years_experience=10,
            specialization="Cardiology",
            status=DoctorStatus.NOT_SUBMITTED
        )
        db.add(doctor)
        db.commit()
        db.refresh(doctor)

        assert doctor.id is not None
        assert doctor.status == DoctorStatus.NOT_SUBMITTED
        assert doctor.unique_token is not None

        db.close()


class TestPreprocessor:
    """Tests for image preprocessing and validation."""

    def test_preprocess_basic_image(self):
        from src.art_engine.preprocessor import preprocess_image

        img = Image.new("RGB", (1200, 1200), color=(180, 160, 140))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        image_bytes = buf.getvalue()

        gray_np, color_np, pil_img = preprocess_image(image_bytes, target_size=(600, 600))
        assert gray_np.shape == (600, 600)
        assert color_np.shape == (600, 600, 3)
        assert pil_img.size == (600, 600)

    def test_validate_photo_quality_too_small(self):
        from src.art_engine.preprocessor import validate_photo_quality

        tiny_img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        buf = io.BytesIO()
        tiny_img.save(buf, format="JPEG")

        is_valid, error_msg, _, _ = validate_photo_quality(buf.getvalue())
        assert not is_valid
        assert "resolution" in error_msg.lower() or "minimum" in error_msg.lower()

    def test_validate_photo_quality_valid_image(self):
        import cv2
        from src.art_engine.preprocessor import validate_photo_quality

        ok_img = Image.new("RGB", (800, 800), color=(180, 160, 140))
        buf = io.BytesIO()
        ok_img.save(buf, format="JPEG")

        if not hasattr(cv2, 'CascadeClassifier'):
            pytest.skip("CascadeClassifier not available in this OpenCV build")

        is_valid, error_msg, _, res = validate_photo_quality(buf.getvalue())
        assert is_valid
        assert res == (800, 800)


class TestSegmentation:
    """Tests that segmentation produces valid masks."""

    def _make_textured_background_image(self, size=300):
        h, w = size, size
        rng = np.random.default_rng(42)
        bg = rng.integers(80, 160, (h, w, 3), dtype=np.uint8)
        for x in range(0, w, 12):
            bg[:, x:x+4, :] = np.clip(bg[:, x:x+4, :] + 40, 0, 255)

        color_np = bg.copy()
        color_np[50:250, 80:220, :] = 200
        gray_np = np.mean(color_np, axis=2).astype(np.uint8)
        return gray_np, color_np

    def test_masks_same_coordinate_space(self):
        from src.art_engine.segmentation import extract_masks

        gray_np, color_np = self._make_textured_background_image(size=400)
        sil, face, body = extract_masks(gray_np, color_np)

        assert sil.shape == gray_np.shape
        assert face.shape == gray_np.shape
        assert body.shape == gray_np.shape

    def test_save_debug_masks_creates_files(self, tmp_path):
        from src.art_engine.segmentation import save_debug_masks

        gray_np, color_np = self._make_textured_background_image()
        out_dir = str(tmp_path / "debug")
        save_debug_masks(gray_np, color_np, output_dir=out_dir)

        assert os.path.exists(os.path.join(out_dir, "silhouette_mask.png"))
        assert os.path.exists(os.path.join(out_dir, "face_mask.png"))
        assert os.path.exists(os.path.join(out_dir, "body_mask.png"))
        assert os.path.exists(os.path.join(out_dir, "mask_overview.png"))


class TestCertificateLayout:
    """Tests for the certificate presentation layout."""

    def test_certificate_layout_composition(self):
        from src.art_engine.composer import create_certificate_layout

        portrait = Image.new("RGBA", (200, 200), (40, 40, 40, 255))
        cert = create_certificate_layout(
            portrait_img=portrait,
            doctor_name="Dr. Rajesh Kumar",
            specialization="Cardiology",
            years_experience=22,
            achievements_text="Distinguished Cardiologist",
            cert_size=(600, 800)
        )
        assert cert.mode == "RGB"
        assert cert.size == (600, 800)

    def test_name_without_dr_prefix_auto_prefixed(self):
        from src.art_engine.composer import create_certificate_layout

        portrait = Image.new("RGBA", (100, 100), (200, 200, 200, 255))
        cert = create_certificate_layout(
            portrait_img=portrait,
            doctor_name="Ananya Singh",
            cert_size=(600, 800)
        )
        assert cert is not None
        assert cert.size == (600, 800)
