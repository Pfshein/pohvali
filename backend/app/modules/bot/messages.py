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
