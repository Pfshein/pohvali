"""Shell command for changing the role of an existing user account."""

import argparse
import asyncio
import sys

from app.core.db import get_session_factory
from app.modules.users.models import UserRole
from app.modules.users.service import UserNotFound, set_user_role


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # noqa: ARG002
        # Do not echo untrusted arguments (Telegram IDs) to process output.
        self.exit(2, "Invalid arguments.\n")


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("positive integer required") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("positive integer required")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="set_role", add_help=True)
    parser.add_argument("telegram_id", type=_positive_integer)
    parser.add_argument("role", choices=[role.value for role in UserRole])
    return parser


async def _set_role(telegram_id: int, role: str) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            await set_user_role(
                session,
                telegram_id=telegram_id,
                role=UserRole(role),
            )
        except UserNotFound:
            print(
                "User account not found. Ask them to open the bot or Mini App first.",
                file=sys.stderr,
            )
            return 1
    print("User role updated.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(_set_role(args.telegram_id, args.role))


if __name__ == "__main__":
    raise SystemExit(main())
