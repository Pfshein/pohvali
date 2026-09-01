from app.modules.bot.add_mascot import (
    DENIED_TEXT,
    AdminCommand,
    AdminCommandRefused,
    parse_add_mascot,
)
from app.modules.bot.messages import FORBIDDEN_TONE_WORDS

ADMIN_IDS = frozenset({700})
VALID_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 48


def add_mascot_update(
    *,
    caption: str = "/add_mascot umka 40 | Умка | Тихий и загадочный",
    chat_type: str = "private",
    from_id: int = 700,
    with_document: bool = True,
    file_size: int | None = 2048,
) -> dict:
    document = None
    if with_document:
        document = {"file_id": "AgAC-file-id", "file_unique_id": "unique", "mime_type": "image/png"}
        if file_size is not None:
            document["file_size"] = file_size
    message: dict = {
        "message_id": 5,
        "date": 1_700_000_000,
        "chat": {"id": from_id, "type": chat_type},
        "from": {"id": from_id, "is_bot": False},
        "caption": caption,
    }
    if document is not None:
        message["document"] = document
    return {"update_id": 900, "message": message}


def test_valid_admin_command_is_parsed() -> None:
    command = parse_add_mascot(add_mascot_update(), admin_ids=ADMIN_IDS)

    assert isinstance(command, AdminCommand)
    assert command.chat_id == 700
    assert command.file_id == "AgAC-file-id"
    assert command.code == "umka"
    assert command.unlock_threshold == 40
    assert command.name == "Умка"
    assert command.blurb == "Тихий и загадочный"


def test_command_accepts_bot_mention() -> None:
    command = parse_add_mascot(
        add_mascot_update(caption="/add_mascot@PohvaliSebyaBot umka 40 | Умка | Тихий"),
        admin_ids=ADMIN_IDS,
    )

    assert isinstance(command, AdminCommand)
    assert command.code == "umka"


def test_non_admin_gets_calm_denial() -> None:
    result = parse_add_mascot(add_mascot_update(from_id=42), admin_ids=ADMIN_IDS)

    assert isinstance(result, AdminCommandRefused)
    assert result.chat_id == 42
    assert result.text == DENIED_TEXT


def test_group_chat_is_ignored() -> None:
    assert (
        parse_add_mascot(add_mascot_update(chat_type="group"), admin_ids=ADMIN_IDS) is None
    )


def test_updates_without_command_caption_are_ignored() -> None:
    assert parse_add_mascot({"update_id": 1}, admin_ids=ADMIN_IDS) is None
    assert (
        parse_add_mascot(
            add_mascot_update(caption="просто подпись без команды"), admin_ids=ADMIN_IDS
        )
        is None
    )
    assert (
        parse_add_mascot(
            add_mascot_update(caption="/add_mascotty umka 40 | Умка | Тихий"),
            admin_ids=ADMIN_IDS,
        )
        is None
    )


def test_command_without_document_is_refused_with_guidance() -> None:
    result = parse_add_mascot(add_mascot_update(with_document=False), admin_ids=ADMIN_IDS)

    assert isinstance(result, AdminCommandRefused)
    assert "PNG" in result.text


def test_oversized_file_hint_is_refused_early() -> None:
    result = parse_add_mascot(
        add_mascot_update(file_size=2 * 1024 * 1024), admin_ids=ADMIN_IDS
    )

    assert isinstance(result, AdminCommandRefused)
    assert "1 MiB" in result.text


def test_format_errors_explain_what_to_fix() -> None:
    cases = {
        "/add_mascot umka сорок | Умка | Тихий": "порог",
        "/add_mascot umka 0 | Умка | Тихий": "порог",
        "/add_mascot Umka 40 | Умка | Тихий": "code",
        "/add_mascot u 40 | Умка | Тихий": "code",
        "/add_mascot umka 40 | | Тихий": "имя",
        "/add_mascot umka 40 | Умка |": "описани",
        "/add_mascot umka 40 | Умка": "формат",
        "/add_mascot 40 | Умка | Тихий": "формат",
    }
    for caption, expected_fragment in cases.items():
        result = parse_add_mascot(add_mascot_update(caption=caption), admin_ids=ADMIN_IDS)
        assert isinstance(result, AdminCommandRefused), caption
        assert expected_fragment in result.text.casefold(), caption


def test_boundary_lengths_are_accepted() -> None:
    max_name = "И" * 64
    max_blurb = "О" * 160
    command = parse_add_mascot(
        add_mascot_update(caption=f"/add_mascot umka 40 | {max_name} | {max_blurb}"),
        admin_ids=ADMIN_IDS,
    )

    assert isinstance(command, AdminCommand)
    assert command.name == max_name
    assert command.blurb == max_blurb


def test_too_long_name_or_blurb_is_refused() -> None:
    for caption in (
        f"/add_mascot umka 40 | {'И' * 65} | Тихий",
        f"/add_mascot umka 40 | Умка | {'О' * 161}",
    ):
        result = parse_add_mascot(add_mascot_update(caption=caption), admin_ids=ADMIN_IDS)
        assert isinstance(result, AdminCommandRefused), caption


def test_admin_copy_keeps_calm_pressure_free_tone() -> None:
    from app.modules.bot.messages import (
        ADD_MASCOT_ALREADY_TEXT,
        ADD_MASCOT_CREATED_PREFIX,
        ADD_MASCOT_RETRY_TEXT,
    )

    admin_texts = (
        DENIED_TEXT,
        ADD_MASCOT_RETRY_TEXT,
        ADD_MASCOT_ALREADY_TEXT,
        ADD_MASCOT_CREATED_PREFIX,
    )
    for text in admin_texts:
        lowered = text.casefold()
        for word in FORBIDDEN_TONE_WORDS:
            assert word.casefold() not in lowered
