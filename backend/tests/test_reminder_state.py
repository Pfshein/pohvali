from app.modules.reminders.state import (
    ReminderPhase,
    faded,
    is_terminal,
    reactivated,
)


def test_fade_follows_the_documented_one_way_path() -> None:
    assert faded(ReminderPhase.ACTIVE) is ReminderPhase.DORMANT
    assert faded(ReminderPhase.DORMANT) is ReminderPhase.SILENT


def test_silent_is_terminal_and_does_not_fade_further() -> None:
    assert faded(ReminderPhase.SILENT) is ReminderPhase.SILENT
    assert is_terminal(ReminderPhase.SILENT) is True
    assert is_terminal(ReminderPhase.ACTIVE) is False
    assert is_terminal(ReminderPhase.DORMANT) is False


def test_active_to_silent_is_reachable_by_repeated_fade() -> None:
    phase = ReminderPhase.ACTIVE
    seen = [phase]
    for _ in range(3):
        phase = faded(phase)
        seen.append(phase)
    assert seen[:3] == [
        ReminderPhase.ACTIVE,
        ReminderPhase.DORMANT,
        ReminderPhase.SILENT,
    ]
    # Once silent, further fades are a no-op.
    assert seen[3] is ReminderPhase.SILENT


def test_reengagement_resets_to_active() -> None:
    assert reactivated() is ReminderPhase.ACTIVE
