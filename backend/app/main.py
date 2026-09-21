from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .routers import auth, properties, users

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="OsonIjara API",
    description="Backend for the OsonIjara rental-listing app.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-friendly; tighten this before shipping to production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(properties.router)


@app.on_event("startup")
def on_startup() -> None:
    # Simple MVP approach: create tables directly from the models.
    # Swap this for Alembic migrations once the schema needs to evolve safely.
    Base.metadata.create_all(bind=engine)


@app.get("/")
def health_check():
    return {"message": "OsonIjara API ishlayapti", "docs": "/docs"}
