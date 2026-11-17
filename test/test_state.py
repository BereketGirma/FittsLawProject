import pytest

from fitts.core.state import AppState, ParticipantSession, StateMachine


def test_basic_application_state_transitions():
    machine = StateMachine()
    machine.transition(AppState.CONSENT)
    machine.transition(AppState.DEMOGRAPHICS)
    machine.transition(AppState.INSTRUCTIONS)
    machine.transition(AppState.PRACTICE)
    assert machine.state is AppState.PRACTICE


def test_invalid_state_transition_is_rejected():
    with pytest.raises(ValueError, match="invalid transition"):
        StateMachine().transition(AppState.PRACTICE)


def test_participant_id_remains_consistent():
    session = ParticipantSession()
    original_id = session.participant_id
    machine = StateMachine()
    machine.transition(AppState.CONSENT)
    machine.transition(AppState.DEMOGRAPHICS)
    machine.transition(AppState.INSTRUCTIONS)
    machine.transition(AppState.DEMOGRAPHICS)
    assert session.participant_id == original_id
