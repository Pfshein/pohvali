"""User-facing bot copy.

The tone must stay calm and pressure-free: no streaks, no missed days, no
guilt, no personality judgements or advice given from a psychologist's voice
(see ``AGENTS.md`` product guardrails and backlog task PH-604).
"""

START_GREETING = (
    "Привет. Это тихое место, чтобы раз в день заметить, за что можно "
    "похвалить себя сегодня. Без оценок и без спешки — можно даже за мелочь."
)

# Evening nudge (PH-503). Calm and optional; never implies obligation.
REMINDER_NUDGE = (
    "Тихая минутка на вечер. Если захочется, можно заметить, за что "
    "похвалить себя сегодня — даже за мелочь. А не захочется — тоже хорошо."
)

# One-time gentle message when a fading reminder goes quiet for good (PH-503).
REMINDER_RETURN = (
    "Мы оставляем дверь открытой. Если однажды захочется вернуться — это "
    "место будет ждать, спокойно и без напоминаний."
)

OPEN_BUTTON_TEXT = "Открыть"

# Guard words that must never appear in bot copy. Referenced by tone tests so a
# future copy change cannot quietly reintroduce pressure wording.
FORBIDDEN_TONE_WORDS = ("серия", "серию", "пропустил", "не потеряй", "не теряй")

# Admin catalog maintenance (PH-405). Calm and specific: errors explain what
# to fix without pressure and without revealing admin identities.
ADD_MASCOT_DENIED = "Эта команда доступна только администратору сервиса."
ADD_MASCOT_NEED_DOCUMENT = "Приложи PNG-файл документом к команде /add_mascot."
ADD_MASCOT_TOO_BIG = "Файл больше 1 MiB — сожми PNG и попробуй ещё раз."
ADD_MASCOT_RETRY_TEXT = "Не удалось получить файл. Можно спокойно попробовать ещё раз."
ADD_MASCOT_ALREADY_TEXT = "Такой маскот уже есть в каталоге — ничего не изменилось."
ADD_MASCOT_CREATED_PREFIX = "Готово: маскот добавлен в каталог и уже виден всем."
ADD_MASCOT_FORMAT = "Формат: /add_mascot code порог | Имя | Описание"
ADD_MASCOT_CODE_INVALID = (
    "code должен быть 2–32 символа: маленькие латинские буквы, цифры и _, "
    "начиная с буквы."
)
ADD_MASCOT_THRESHOLD_INVALID = "порог должен быть положительным целым числом."
ADD_MASCOT_NAME_INVALID = "имя должно быть непустым и не длиннее 64 символов."
ADD_MASCOT_BLURB_INVALID = "описание должно быть непустым и не длиннее 160 символов."

# Aggregated service statistics (PH-802). The same denial is used for unknown
# accounts and regular users so command handling does not reveal account state.
STATS_DENIED = "Эта команда доступна только администратору сервиса."
STATS_USAGE = "Формат: /stats или /stats 30"
STATS_RETRY = "Не удалось получить статистику. Можно спокойно попробовать ещё раз."
