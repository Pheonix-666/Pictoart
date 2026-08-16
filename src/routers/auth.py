import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from src.config import settings
from src.database import get_db
from src.models import AdminUser, AdminRole, AuditLog

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def get_current_admin_user(request: Request, db: Session = Depends(get_db)) -> Optional[AdminUser]:
    """
    Retrieves current authenticated admin user from session cookie or Authorization header.
    """
    token = request.cookies.get("admin_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if not email:
            return None
        admin = db.query(AdminUser).filter(AdminUser.email == email).first()
        return admin
    except Exception:
        return None

def require_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    admin = get_current_admin_user(request, db)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return admin

def require_super_admin(admin: AdminUser = Depends(require_admin)) -> AdminUser:
    if admin.role != AdminRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin permissions required"
        )
    return admin

def log_audit_action(db: Session, admin: Optional[AdminUser], action: str, target_doctor_id: Optional[int] = None, details: Optional[str] = None):
    audit = AuditLog(
        admin_id=admin.id if admin else None,
        admin_email=admin.email if admin else "system",
        action=action,
        target_doctor_id=target_doctor_id,
        details=details
    )
    db.add(audit)
    db.commit()
