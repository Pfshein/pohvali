from fastapi import APIRouter

from app.api.v1.calendar import router as calendar_router
from app.api.v1.health import router as health_router
from app.api.v1.mascots import router as mascots_router
from app.api.v1.praises import router as praises_router
from app.api.v1.reminders import router as reminders_router
from app.api.v1.session import router as session_router
from app.api.v1.telegram import router as telegram_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(session_router)
router.include_router(praises_router)
router.include_router(calendar_router)
router.include_router(mascots_router)
router.include_router(reminders_router)
router.include_router(telegram_router)
