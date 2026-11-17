"""Validated participant responses. No direct identifiers are requested."""

from dataclasses import dataclass

COMPUTER_HOURS = ("Less than 5 hours", "5–10 hours", "11–20 hours", "21–40 hours",
                  "More than 40 hours", "Prefer not to answer")


@dataclass(frozen=True, slots=True)
class Demographics:
    participant_id: str
    age: int | None
    computer_hours_per_week: str
    mouse_hand: str
    dominant_hand: str | None = None

    def __post_init__(self):
        if self.age is not None and (type(self.age) is not int or not 1 <= self.age <= 120):
            raise ValueError("Enter an age between 1 and 120, or leave blank to decline.")
        if self.computer_hours_per_week not in COMPUTER_HOURS:
            raise ValueError("Select weekly computer usage.")
        if self.mouse_hand not in {"Left", "Right"}:
            raise ValueError("Select the hand you will use on the trackpad.")
        if self.dominant_hand not in {None, "Left", "Right", "Ambidextrous"}:
            raise ValueError("Invalid dominant hand.")
