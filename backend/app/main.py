import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.database import Base, engine
from app.limiter import limiter
from app.routers import auth, etudiants, annonces, entreprises, club, validation, notifications
from app.routers.etudiants import cv_router
from app.services import storage_service

# Import all models so Alembic/SQLAlchemy sees them
import app.models  # noqa: F401

app = FastAPI(
    title="EnimConnect API",
    description="Plateforme de mise en relation étudiants-entreprises — ENSMR",
    version="1.0.0",
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — only allow configured frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create local storage dirs (used as fallback when STORAGE_BACKEND=local)
storage_path = settings.STORAGE_PATH
os.makedirs(os.path.join(storage_path, "cvs"), exist_ok=True)
os.makedirs(os.path.join(storage_path, "photos"), exist_ok=True)
os.makedirs(os.path.join(storage_path, "logos"), exist_ok=True)

# Static mounts for photos/logos (always local, even when CVs use S3)
app.mount("/storage/photos", StaticFiles(directory=os.path.join(storage_path, "photos")), name="photos")
app.mount("/storage/logos", StaticFiles(directory=os.path.join(storage_path, "logos")), name="logos")

# Routers
app.include_router(auth.router)
app.include_router(etudiants.router)
app.include_router(cv_router)
app.include_router(annonces.router)
app.include_router(entreprises.router)
app.include_router(club.router)
app.include_router(validation.router)
app.include_router(validation.router, prefix="/api")  # JSON endpoints: /api/decision/{id}
app.include_router(notifications.router)


@app.get("/api/photos/{user_id}")
def serve_photo(user_id: str):
    result = storage_service.read_photo(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    content, content_type = result
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/logos/{entreprise_id}")
def serve_logo(entreprise_id: str):
    result = storage_service.read_logo(entreprise_id)
    if not result:
        raise HTTPException(status_code=404, detail="Logo introuvable")
    content, content_type = result
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/health")
def health():
    return {"status": "ok", "service": "EnimConnect API"}
