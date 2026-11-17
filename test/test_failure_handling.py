"""Persistence failure, analysis exclusion, and state machine integration."""

import json

import pygame
import pytest

from fitts.analysis.metrics import path_length, shannon_id
from fitts.core.state import AppState
from fitts.core.trial_generator import generate_experiment_trials
from fitts.data.recorder import recover_session
from test_experiment import config, make_manager, read_csv
from fitts.main import Application


def test_known_path_and_difficulty():
    assert path_length([(0, 0), (3, 4), (6, 8)]) == 10
    assert path_length([]) == 0
    assert path_length([(1, 1)]) == 0
    assert shannon_id(150, 50) == 2
    with pytest.raises(ValueError):
        shannon_id(150, 0)


def test_saved_seed_and_actual_order(tmp_path, config):
    manager = make_manager(tmp_path, config)
    saved = json.loads((manager.recorder.folder / "session.json").read_text())
    assert saved["random_seed"] == config.random_seed
    rows = read_csv(manager.recorder.folder / "trial_sequence.csv")
    assert [(row["direction"], int(row["target_width_px"]), int(row["target_distance_px"])) for row in rows] == [
        (t.condition.direction, t.condition.target_width, t.condition.distance) for t in generate_experiment_trials(config)]
    with pytest.raises(RuntimeError, match="regenerated"):
        manager.recorder.save_schedule(manager.schedule, manager.window_size)


def test_incomplete_session_rejected_by_analysis(tmp_path, config):
    from fitts.analysis.statistics import load_session, validate_completed_session
    manager = make_manager(tmp_path, config)
    manager.stop("withdrawn")
    session, frames = load_session(manager.recorder.folder)
    with pytest.raises(ValueError, match="not finalized and completed"):
        validate_completed_session(session, frames)


def test_journal_recovers_failed_csv_append(tmp_path, config, monkeypatch):
    manager = make_manager(tmp_path, config)
    manager.start(manager.center, 0)
    import fitts.data.recorder as module
    original = module.write_csv
    def fail_trials(path, *args, **kwargs):
        if path.name == "trials.csv":
            raise OSError("simulated disk failure")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(module, "write_csv", fail_trials)
    with pytest.raises(OSError):
        manager.click(manager.current.condition.circle(*manager.window_size)[0], 10_000_000)
    assert not manager.finished
    assert not manager.recorder.finalized
    monkeypatch.setattr(module, "write_csv", original)
    recover_session(manager.recorder.folder, tmp_path / "recovered")
    rows = read_csv(tmp_path / "recovered" / "trials.csv")
    assert len(rows) == 1 and rows[0]["status"] == "completed"
    assert len(read_csv(tmp_path / "recovered" / "clicks.csv")) == 1


def test_application_finalization_failure_cannot_show_success(tmp_path, config, monkeypatch):
    pygame.init()
    try:
        app = Application(config, data_path=tmp_path)
        manager = make_manager(tmp_path, config, "failure-test")
        app.session.participant_id = "failure-test"
        app.session.has_consented = True
        app.recorder, app.manager = manager.recorder, manager
        from fitts.ui.experiment import ExperimentScreen
        app.machine.state = AppState.EXPERIMENT
        app.screens[AppState.EXPERIMENT] = ExperimentScreen(app.screen, app.fonts, "failure-test", manager)
        manager.index = 319
        manager.recorder.session["completed_trials"] = 319
        manager.start(manager.center)
        def fail_finalization(status):
            raise OSError("simulated finalization failure")
        monkeypatch.setattr(manager.recorder, "finalize", fail_finalization)
        target = manager.current.condition.circle(*manager.window_size)[0]
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=target))
        assert app.persistence_error == "simulated finalization failure"
        assert not manager.finished and not manager.recorder.finalized
        assert AppState.COMPLETE not in app.screens
    finally:
        pygame.quit()


def test_ui_block_break_and_completion(tmp_path, config):
    pygame.init()
    try:
        app = Application(config, data_path=tmp_path)
        manager = make_manager(tmp_path, config, "ui-test")
        app.session.has_consented = True
        app.recorder, app.manager = manager.recorder, manager
        from fitts.ui.experiment import ExperimentScreen
        screen = ExperimentScreen(app.screen, app.fonts, "ui-test", manager)
        app.screens[AppState.EXPERIMENT] = app.screens[AppState.BREAK] = screen
        app.machine.state = AppState.EXPERIMENT
        for number in range(320):
            if number and number % 32 == 0:
                assert app.machine.state is AppState.BREAK
                screen.render()
                click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=screen.continue_button().rect.center)
                app.handle_event(click)
                assert app.machine.state is AppState.BREAK
                screen.break_ready_at = 0
                app.handle_event(click)
            app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=manager.center))
            app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=manager.current.condition.circle(*manager.window_size)[0]))
        assert app.machine.state is AppState.COMPLETE
        assert not app.persistence_error
        app.screens[AppState.COMPLETE].render()
        assert json.loads((manager.recorder.folder / "session.json").read_text())["status"] == "completed"
        with pytest.raises(ValueError, match="finalized"):
            recover_session(manager.recorder.folder, tmp_path / "invalid_recovery")
    finally:
        pygame.quit()
