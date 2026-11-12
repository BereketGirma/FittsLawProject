import pygame

from fitts.core.config import load_config
from fitts.core.state import AppState
from fitts.main import Application


def test_application_does_not_save_before_agreement(tmp_path):
    pygame.init()
    try:
        app = Application(load_config("config/experiment.json"), data_path=tmp_path)
        participant_id = app.session.participant_id
        app.transition(AppState.CONSENT)
        assert not app.consent_store.path_for(participant_id).exists()
        assert {screen.participant_id for screen in app.screens.values()} == {participant_id}
    finally:
        pygame.quit()
