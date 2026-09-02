"""Pure parsing and formatting for the private ``/stats`` command."""

import re
from dataclasses import dataclass

from app.modules.admin_stats.service import PeriodStats, StatsSnapshot
from app.modules.bot.messages import STATS_DENIED, STATS_USAGE

_COMMAND_TOKEN = re.compile(r"/stats(?:@[A-Za-z0-9_]+)?$")


@dataclass(frozen=True, slots=True)
class StatsCommand:
    chat_id: int
    days: int | None = None


@dataclass(frozen=True, slots=True)
class StatsCommandRefused:
    chat_id: int
    text: str


def _command_token(text: str) -> bool:
    token = text.strip().split(maxsplit=1)[0] if text.strip() else ""
    return _COMMAND_TOKEN.fullmatch(token) is not None


def extract_stats_actor_id(update: dict) -> int | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat")
    if not isinstance(chat, dict) or chat.get("type") != "private":
        return None
    text = message.get("text")
    if not isinstance(text, str) or not _command_token(text):
        return None
    author = message.get("from")
    actor_id = author.get("id") if isinstance(author, dict) else None
    return actor_id if type(actor_id) is int else None


def parse_stats_command(
    update: dict,
    *,
    authorized: bool,
) -> StatsCommand | StatsCommandRefused | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat")
    if not isinstance(chat, dict) or chat.get("type") != "private":
        return None
    chat_id = chat.get("id")
    text = message.get("text")
    if type(chat_id) is not int or not isinstance(text, str) or not _command_token(text):
        return None
    if not authorized:
        return StatsCommandRefused(chat_id, STATS_DENIED)
    parts = text.strip().split()
    if len(parts) == 1:
        return StatsCommand(chat_id)
    if len(parts) == 2 and parts[1] == "30":
        return StatsCommand(chat_id, days=30)
    return StatsCommandRefused(chat_id, STATS_USAGE)


def _percent(numerator: int, denominator: int) -> str:
    value = (numerator / denominator * 100) if denominator else 0.0
    return f"{value:.1f}".replace(".", ",") + "%"


def _period_text(label: str, stats: PeriodStats) -> str:
    return "\n".join(
        (
            label,
            f"• Открыли приложение: {stats.opened_users}",
            f"• Оставили похвалу: {stats.praised_users}",
            f"• Всего похвал: {stats.praises}",
            f"• Конверсия: {_percent(stats.praised_users, stats.opened_users)}",
        )
    )


def format_stats(
    snapshot: StatsSnapshot,
    *,
    days: int | None = None,
) -> str:
    period = snapshot.last_30_days if days == 30 else snapshot.last_7_days
    blocks = []
    if days == 30:
        blocks.append(_period_text("Последние 30 дней (UTC)", period))
    else:
        blocks.extend(
            (
                _period_text("Сегодня (UTC)", snapshot.today),
                _period_text("Последние 7 дней (UTC)", period),
            )
        )
    all_time = snapshot.all_time
    blocks.append(
        "\n".join(
            (
                "За всё время",
                f"• Пользователей: {all_time.opened_users}",
                f"• Оставили хотя бы одну похвалу: {all_time.praised_users}",
                f"• Всего похвал: {all_time.praises}",
                f"• Конверсия: {_percent(all_time.praised_users, all_time.opened_users)}",
            )
        )
    )
    return "\n\n".join(blocks)
