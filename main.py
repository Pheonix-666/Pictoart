import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.config import settings
from src.database import engine, Base
from src.routers import public, admin

# ----- Create all database tables on startup -----
Base.metadata.create_all(bind=engine)

# ----- Rate Limiter (TICKET-031) -----
limiter = Limiter(key_func=get_remote_address, default_limits=["200/day"])

# ----- FastAPI Application -----
app = FastAPI(
    title=settings.APP_NAME,
    description="Doctor Word-Art Certificate Generator — automated typographic portrait system.",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# Attach rate limiter to app state so SlowAPI decorators work
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ----- Static Files & Templates -----
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# ----- Register Routers -----
app.include_router(public.router)
app.include_router(admin.router)

# ----- Root Redirect -----
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/admin/login")

# ----- Health Check -----
@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
