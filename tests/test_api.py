import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from main import app
from src.database import SessionLocal, Base, engine
from src.models import Doctor, DoctorStatus, AdminUser, AdminRole
from src.routers.auth import hash_password

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup after test if needed

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_public_upload_link_not_found():
    response = client.get("/upload/invalid-token-123")
    assert response.status_code == 404
    assert "Link Invalid" in response.text

def test_admin_login_and_import():
    db = SessionLocal()
    # Create test admin
    existing = db.query(AdminUser).filter(AdminUser.email == "testadmin@vendor.com").first()
    if not existing:
        admin = AdminUser(
            email="testadmin@vendor.com",
            password_hash=hash_password("Pass1234"),
            role=AdminRole.ADMIN
        )
        db.add(admin)
        db.commit()
    db.close()

    # Login
    login_res = client.post(
        "/admin/login",
        data={"email": "testadmin@vendor.com", "password": "Pass1234"},
        follow_redirects=False
    )
    assert login_res.status_code == 303
    assert "admin_session" in login_res.cookies

    session_cookie = login_res.cookies["admin_session"]

    # Import doctors CSV
    csv_content = "name,contact,years_experience,specialization,achievements_text\nDr. Test Doctor,+91-9000000000,10,Cardiology,Top Doctor"
    import_res = client.post(
        "/admin/import",
        files={"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")},
        cookies={"admin_session": session_cookie}
    )
    assert import_res.status_code == 200
    assert "Successfully imported 1 doctors!" in import_res.text
