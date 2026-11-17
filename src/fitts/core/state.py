"""Application/session state definitions and guarded transitions."""

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto


class AppState(Enum):
    WELCOME = auto()
    CONSENT = auto()
    DEMOGRAPHICS = auto()
    INSTRUCTIONS = auto()
    PRACTICE = auto()
    EXPERIMENT = auto()
    BREAK = auto()
    COMPLETE = auto()
    ABORTED = auto()


ALLOWED_TRANSITIONS = {
    AppState.WELCOME: {AppState.CONSENT, AppState.ABORTED},
    AppState.CONSENT: {AppState.WELCOME, AppState.DEMOGRAPHICS, AppState.ABORTED},
    AppState.DEMOGRAPHICS: {AppState.CONSENT, AppState.INSTRUCTIONS, AppState.ABORTED},
    AppState.INSTRUCTIONS: {AppState.DEMOGRAPHICS, AppState.PRACTICE, AppState.ABORTED},
    AppState.PRACTICE: {AppState.INSTRUCTIONS, AppState.EXPERIMENT, AppState.ABORTED},
    AppState.EXPERIMENT: {AppState.BREAK, AppState.COMPLETE, AppState.ABORTED},
    AppState.BREAK: {AppState.EXPERIMENT, AppState.ABORTED},
    AppState.COMPLETE: set(),
    AppState.ABORTED: set(),
}


class StateMachine:
    def __init__(self, initial: AppState = AppState.WELCOME) -> None:
        self.state = initial

    def transition(self, destination: AppState) -> None:
        if destination not in ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid transition: {self.state.name} -> {destination.name}")
        self.state = destination


@dataclass(slots=True)
class ParticipantSession:
    """One pseudonymous ID is retained throughout all onboarding screens."""

    participant_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    has_consented: bool = False
