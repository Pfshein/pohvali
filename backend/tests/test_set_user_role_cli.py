from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.users.models import UserRole
from app.modules.users.service import UserNotFound
from app.modules.users.set_role import build_parser, main


def test_parser_accepts_positive_id_and_role() -> None:
    args = build_parser().parse_args(["700", "admin"])

    assert args.telegram_id == 700
    assert args.role == "admin"


@pytest.mark.parametrize("argv", [["0", "admin"], ["700", "owner"], ["700"]])
def test_parser_rejects_invalid_arguments(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(argv)

    assert error.value.code != 0
    assert "700" not in capsys.readouterr().err


def test_main_updates_existing_role_without_echoing_sensitive_values(capsys) -> None:
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    with (
        patch("app.modules.users.set_role.get_session_factory", return_value=lambda: session),
        patch("app.modules.users.set_role.set_user_role", new=AsyncMock()) as setter,
    ):
        assert main(["700", "admin"]) == 0

    setter.assert_awaited_once_with(session, telegram_id=700, role=UserRole.ADMIN)
    output = capsys.readouterr()
    assert "700" not in output.out + output.err
    assert "DATABASE_URL" not in output.out + output.err


def test_main_reports_missing_account_without_echoing_id(capsys) -> None:
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    with (
        patch("app.modules.users.set_role.get_session_factory", return_value=lambda: session),
        patch(
            "app.modules.users.set_role.set_user_role",
            new=AsyncMock(side_effect=UserNotFound),
        ),
    ):
        assert main(["700", "user"]) == 1

    output = capsys.readouterr()
    assert "700" not in output.out + output.err
    assert "open the bot or Mini App" in output.err
