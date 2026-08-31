import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.api.dependencies import ReplySenderDependency, SettingsDependency
from app.modules.bot.service import build_start_reply

logger = logging.getLogger("app.telegram.webhook")

router = APIRouter(tags=["telegram"])


@router.post("/telegram/{secret_path}", include_in_schema=False)
async def telegram_webhook(
    secret_path: str,
    request: Request,
    settings: SettingsDependency,
    send_reply: ReplySenderDependency,
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
        await send_reply(reply)

    # Always acknowledge so Telegram does not retry a delivered update.
    return Response(status_code=status.HTTP_200_OK)
