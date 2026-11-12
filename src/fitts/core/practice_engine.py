"""UI-independent state for practice pointing trials."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from fitts.core.trial import Trial


class PracticePhase(Enum):
    WAITING_FOR_CENTER = auto()
    TARGET_ACTIVE = auto()
    COMPLETE = auto()


@dataclass(frozen=True, slots=True)
class PracticeResult:
    hit: bool
    advanced: bool


class PracticeEngine:
    def __init__(self, trials: list[Trial]) -> None:
        if not trials:
            raise ValueError("practice requires at least one trial")
        self.trials = trials
        self.index = 0
        self.phase = PracticePhase.WAITING_FOR_CENTER
        self.misses = 0

    @property
    def current_trial(self) -> Trial:
        return self.trials[self.index]

    def activate_target(self) -> None:
        if self.phase is PracticePhase.WAITING_FOR_CENTER:
            self.phase = PracticePhase.TARGET_ACTIVE

    def target_click(self, hit: bool) -> PracticeResult:
        if self.phase is not PracticePhase.TARGET_ACTIVE:
            return PracticeResult(hit=False, advanced=False)
        if not hit:
            self.misses += 1
            return PracticeResult(hit=False, advanced=False)
        if self.index + 1 >= len(self.trials):
            self.phase = PracticePhase.COMPLETE
        else:
            self.index += 1
            self.phase = PracticePhase.WAITING_FOR_CENTER
        return PracticeResult(hit=True, advanced=True)
