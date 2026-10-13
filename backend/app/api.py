"""All HTTP routes, mounted under /api. Each domain owns its router."""

from fastapi import APIRouter

from app.assistant.routes import router as assistant_router
from app.health.routes import router as health_router
from app.notes.routes import router as notes_router

router = APIRouter(prefix="/api")
router.include_router(health_router)
router.include_router(notes_router)
router.include_router(assistant_router)
