"""Reminder lifecycle state machine (PH-501).

A user's evening reminder fades along a single, one-directional path:

    active ──(reminder ignored)──▶ dormant ──(fade window elapsed)──▶ silent

- ``active``   — the default; the user still gets the gentle 22:00 nudge.
- ``dormant``  — a reminder went unanswered, so the cadence steps down. The
                 exact trigger (an ignored push) is applied by PH-503.
- ``silent``   — after the dormant fade window the bot sends one last calm
                 return message and then never nudges again (PH-503).

The fade never runs backwards on its own. The only way out of ``dormant`` or
``silent`` is the user re-engaging (opening the app / writing a praise), which
:func:`reactivated` resets to ``active``. This module is pure: it owns the
allowed transitions and nothing else, so the rules stay unit-testable and the
scheduler/sender (PH-502/PH-503) build on top of them.
"""

from enum import StrEnum

# Days a reminder stays dormant before the single return message and going
# silent (PH-503). Measured from when the user entered the dormant phase.
DORMANT_TO_SILENT_DAYS = 30


class ReminderPhase(StrEnum):
    ACTIVE = "active"
    DORMANT = "dormant"
    SILENT = "silent"


# The single forward fade step for each phase. ``silent`` is terminal.
_NEXT_ON_FADE: dict[ReminderPhase, ReminderPhase] = {
    ReminderPhase.ACTIVE: ReminderPhase.DORMANT,
    ReminderPhase.DORMANT: ReminderPhase.SILENT,
}


def faded(phase: ReminderPhase) -> ReminderPhase:
    """Advance one step down the fade path; ``silent`` stays ``silent``."""
    return _NEXT_ON_FADE.get(phase, phase)


def reactivated() -> ReminderPhase:
    """Phase after the user re-engages — the fade resets to ``active``."""
    return ReminderPhase.ACTIVE


def is_terminal(phase: ReminderPhase) -> bool:
    """Whether the fade can advance no further from ``phase``."""
    return phase not in _NEXT_ON_FADE
