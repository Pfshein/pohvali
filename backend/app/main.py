import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.core.db import get_session_factory
from app.core.logging import AccessLogMiddleware, configure_logging
from app.modules.bot.messages import OPEN_BUTTON_TEXT
from app.modules.reminders.delivery import deliver_reminders
from app.modules.reminders.scheduler import build_reminder_scheduler
from app.modules.reminders.sender import AiogramReminderSender


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # The in-process reminder scheduler runs everywhere except tests, which
        # drive delivery directly. Requires a single backend instance (PH-705).
        scheduler = None
        if settings.app_env != "test":
            sender = AiogramReminderSender(
                settings.bot_token, settings.app_domain, OPEN_BUTTON_TEXT
            )
            deliver = partial(deliver_reminders, sender=sender, sleep=asyncio.sleep)
            scheduler = build_reminder_scheduler(get_session_factory(), deliver=deliver)
            scheduler.start()
        try:
            yield
        finally:
            if scheduler is not None:
                scheduler.shutdown(wait=False)

    application = FastAPI(
        title="Похвали себя API",
        version="0.1.0",
        docs_url="/api/docs" if settings.app_env != "production" else None,
        openapi_url="/api/openapi.json" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    application.add_middleware(AccessLogMiddleware)
    application.include_router(api_router)
    return application


app = create_app()
