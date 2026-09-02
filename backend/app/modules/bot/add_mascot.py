"""Pure parsing of the admin ``/add_mascot`` command (PH-405).

Given a raw Telegram update (already authenticated by the webhook secret) this
module decides whether the update is an admin catalog command and extracts its
fields. It performs no I/O so the behaviour stays unit-testable, mirroring
``build_start_reply``.
"""

import re
from dataclasses import dataclass

from app.modules.bot.messages import (
    ADD_MASCOT_BLURB_INVALID,
    ADD_MASCOT_CODE_INVALID,
    ADD_MASCOT_DENIED,
    ADD_MASCOT_FORMAT,
    ADD_MASCOT_NAME_INVALID,
    ADD_MASCOT_NEED_DOCUMENT,
    ADD_MASCOT_THRESHOLD_INVALID,
    ADD_MASCOT_TOO_BIG,
)
from app.modules.mascots.png import MAX_IMAGE_BYTES

DENIED_TEXT = ADD_MASCOT_DENIED

_CODE_PATTERN = re.compile(r"[a-z][a-z0-9_]{1,31}")
_MAX_NAME_LENGTH = 64
_MAX_BLURB_LENGTH = 160


def extract_add_mascot_actor_id(update: dict) -> int | None:
    """Return the actor for a private update carrying an add-mascot token."""
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat")
    if not isinstance(chat, dict) or chat.get("type") != "private":
        return None
    caption = message.get("caption")
    if not isinstance(caption, str):
        return None
    command_token = caption.strip().partition(" ")[0].partition("@")[0]
    if command_token != "/add_mascot":
        return None
    author = message.get("from")
    actor_id = author.get("id") if isinstance(author, dict) else None
    return actor_id if type(actor_id) is int else None


@dataclass(frozen=True, slots=True)
class AdminCommand:
    """A fully parsed, authorized command awaiting download and validation."""

    chat_id: int
    file_id: str
    code: str
    unlock_threshold: int
    name: str
    blurb: str


@dataclass(frozen=True, slots=True)
class AdminCommandRefused:
    """A command-shaped update that must be answered with guidance or denial."""

    chat_id: int
    text: str


@dataclass(frozen=True, slots=True)
class AdminReply:
    """A plain bot reply; the optional file id asks the sender to echo a preview."""

    chat_id: int
    text: str
    document_file_id: str | None = None


def parse_add_mascot(
    update: dict,
    *,
    authorized: bool,
) -> AdminCommand | AdminCommandRefused | None:
    """Parse a private-chat ``/add_mascot`` caption, else return ``None``."""
    message = update.get("message")
    if not isinstance(message, dict):
        return None

    chat = message.get("chat")
    if not isinstance(chat, dict) or chat.get("type") != "private":
        return None

    chat_id = chat.get("id")
    if type(chat_id) is not int:
        return None

    caption = message.get("caption")
    if not isinstance(caption, str):
        return None
    command_token = caption.strip().partition(" ")[0].partition("@")[0]
    if command_token != "/add_mascot":
        return None

    if not authorized:
        return AdminCommandRefused(chat_id, DENIED_TEXT)

    document = message.get("document")
    if not isinstance(document, dict) or not isinstance(document.get("file_id"), str):
        return AdminCommandRefused(chat_id, ADD_MASCOT_NEED_DOCUMENT)

    file_size = document.get("file_size")
    if type(file_size) is int and file_size > MAX_IMAGE_BYTES:
        return AdminCommandRefused(chat_id, ADD_MASCOT_TOO_BIG)

    segments = [segment.strip() for segment in caption.strip().split("|")]
    if len(segments) != 3:
        return AdminCommandRefused(chat_id, ADD_MASCOT_FORMAT)
    head = segments[0].split()
    if len(head) != 3:
        return AdminCommandRefused(chat_id, ADD_MASCOT_FORMAT)

    code = head[1]
    threshold_text = head[2]
    name = segments[1]
    blurb = segments[2]

    if _CODE_PATTERN.fullmatch(code) is None:
        return AdminCommandRefused(chat_id, ADD_MASCOT_CODE_INVALID)
    if not threshold_text.isdigit() or int(threshold_text) <= 0:
        return AdminCommandRefused(chat_id, ADD_MASCOT_THRESHOLD_INVALID)
    if not 1 <= len(name) <= _MAX_NAME_LENGTH:
        return AdminCommandRefused(chat_id, ADD_MASCOT_NAME_INVALID)
    if not 1 <= len(blurb) <= _MAX_BLURB_LENGTH:
        return AdminCommandRefused(chat_id, ADD_MASCOT_BLURB_INVALID)

    return AdminCommand(
        chat_id=chat_id,
        file_id=document["file_id"],
        code=code,
        unlock_threshold=int(threshold_text),
        name=name,
        blurb=blurb,
    )
