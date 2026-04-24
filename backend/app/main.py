import logging
import os
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import IMAGES_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(IMAGES_DIR, exist_ok=True)
    yield
    if os.path.exists(IMAGES_DIR):
        shutil.rmtree(IMAGES_DIR)


app = FastAPI(title="IDStorm API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "idstorm-api"}


from app.routers import candidate, dialogue, requirement, session  # noqa: E402

app.include_router(session.router, prefix="/api")
app.include_router(dialogue.router, prefix="/api")
app.include_router(requirement.router, prefix="/api")
app.include_router(candidate.router, prefix="/api")
