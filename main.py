
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.config import settings
from src.database import engine, Base
from src.routers import public, admin


# ============================================================
# DATABASE
# ============================================================

def create_database_tables():
    """Create database tables if they do not already exist."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        raise


create_database_tables()


# ============================================================
# RATE LIMITER
# ============================================================

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/day"],
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Doctor Word-Art Certificate Generator — "
        "automated typographic portrait system."
    ),
    version="1.0.0",

    # Only expose API documentation in development
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)


# ============================================================
# SLOWAPI CONFIGURATION
# ============================================================

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="src/static"),
    name="static",
)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(public.router)
app.include_router(admin.router)


# ============================================================
# ROOT ROUTE
# ============================================================

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(
        url="/admin/login",
        status_code=307,
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
    }


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
