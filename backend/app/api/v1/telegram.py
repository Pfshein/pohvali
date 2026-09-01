import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.api.dependencies import (
    DatabaseSession,
    FileDownloaderDependency,
    ReplySenderDependency,
    SettingsDependency,
)
from app.core.config import Settings
from app.modules.bot.add_mascot import (
    AdminCommandRefused,
    AdminReply,
    parse_add_mascot,
)
from app.modules.bot.messages import (
    ADD_MASCOT_ALREADY_TEXT,
    ADD_MASCOT_CREATED_PREFIX,
    ADD_MASCOT_RETRY_TEXT,
)
from app.modules.bot.service import build_start_reply
from app.modules.mascots.png import validate_png
from app.modules.mascots.service import (
    MascotCodeTaken,
    ThresholdTaken,
    add_mascot,
)
from app.modules.reminders.service import record_dm_available

logger = logging.getLogger("app.telegram.webhook")

router = APIRouter(tags=["telegram"])


@router.post("/telegram/{secret_path}", include_in_schema=False)
async def telegram_webhook(
    secret_path: str,
    request: Request,
    settings: SettingsDependency,
    send_reply: ReplySenderDependency,
    download_file: FileDownloaderDependency,
    session: DatabaseSession,
    secret_token: Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None,
) -> Response:
    # An unguessable path hides the endpoint; the secret header proves the
    # request really came from Telegram. Both are compared in constant time.
    if not hmac.compare_digest(secret_path, settings.telegram_webhook_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not hmac.compare_digest(secret_token or "", settings.telegram_webhook_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    update = await request.json()
    # Never log the update body: it may carry private message text. Only the
    # numeric update id (not PII) is recorded for observability.
    logger.info("telegram webhook update received", extra={"update_id": update.get("update_id")})

    reply = build_start_reply(update, mini_app_url=settings.app_domain)
    if reply is not None:
        # A private-chat /start proves the user can receive bot DMs (PH-501).
        # chat_id in a private chat is the user's Telegram id. Never logged.
        await record_dm_available(session, telegram_id=reply.chat_id)
        await send_reply(reply)

    await _handle_add_mascot(
        update,
        settings=settings,
        session=session,
        download_file=download_file,
        send_reply=send_reply,
    )

    # Always acknowledge so Telegram does not retry a delivered update.
    return Response(status_code=status.HTTP_200_OK)


async def _handle_add_mascot(
    update: dict,
    *,
    settings: Settings,
    session: DatabaseSession,
    download_file: FileDownloaderDependency,
    send_reply: ReplySenderDependency,
) -> None:
    command = parse_add_mascot(update, admin_ids=settings.telegram_admin_id_set)
    if command is None:
        return

    if isinstance(command, AdminCommandRefused):
        logger.info("add_mascot handled", extra={"outcome": "refused"})
        await send_reply(AdminReply(command.chat_id, command.text))
        return

    # From here the update is a parsed admin command; never log its text,
    # author id, file id or image bytes.
    try:
        image_data = await download_file(command.file_id)
    except Exception:
        logger.warning("add_mascot handled", extra={"outcome": "download_failed"})
        await send_reply(AdminReply(command.chat_id, ADD_MASCOT_RETRY_TEXT))
        return

    image_error = validate_png(image_data)
    if image_error is not None:
        logger.info("add_mascot handled", extra={"outcome": "invalid_png"})
        await send_reply(AdminReply(command.chat_id, image_error))
        return

    try:
        created = await add_mascot(
            session,
            code=command.code,
            name=command.name,
            blurb=command.blurb,
            unlock_threshold=command.unlock_threshold,
            image_data=image_data,
        )
    except MascotCodeTaken:
        logger.info("add_mascot handled", extra={"outcome": "code_taken"})
        await send_reply(
            AdminReply(
                command.chat_id,
                f"Маскот с code «{command.code}» уже есть; существующие маскоты "
                "не перезаписываются.",
            )
        )
        return
    except ThresholdTaken:
        logger.info("add_mascot handled", extra={"outcome": "threshold_taken"})
        await send_reply(
            AdminReply(
                command.chat_id,
                f"Порог {command.unlock_threshold} уже занят другим маскотом — "
                "выбери другой порог.",
            )
        )
        return

    logger.info("add_mascot handled", extra={"outcome": "created" if created else "already"})
    if created:
        text = f"{ADD_MASCOT_CREATED_PREFIX} {command.name}, порог {command.unlock_threshold} ⭐."
    else:
        text = ADD_MASCOT_ALREADY_TEXT
    await send_reply(AdminReply(command.chat_id, text, document_file_id=command.file_id))
