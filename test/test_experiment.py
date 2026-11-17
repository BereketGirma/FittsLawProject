"""Deterministic lifecycle, storage, recovery and full-study integration tests."""

import csv
import json
from collections import Counter
from dataclasses import asdict, replace
from itertools import product

import pygame
import pytest

from fitts.core.config import load_config
from fitts.core.device_info import fixed_input_metadata
from fitts.core.experiment_manager import ExperimentManager
from fitts.core.state import AppState
from fitts.core.trial import Trial, circle_contains
from fitts.core.trial_generator import generate_experiment_trials
from fitts.data.consent import ConsentRecord, ConsentStore
from fitts.data.models import COMPUTER_HOURS, Demographics
from fitts.data.recorder import Recorder, recover_session
from fitts.main import Application


@pytest.fixture
def config():
    return load_config("config/experiment.json")


def make_recorder(root, config, participant="test-id"):
    path = ConsentStore(root).save(ConsentRecord.affirmative(participant, "draft-2"))
    recorder = Recorder(path.parent, participant, asdict(config))
    recorder.save_onboarding(Demographics(participant, None, COMPUTER_HOURS[-1], "Right"),
                             {"participant_id": participant, "input_device": "Mouse"})
    return recorder


def make_manager(root, config, participant="test-id"):
    recorder = make_recorder(root, config, participant)
    schedule = generate_experiment_trials(config)
    size = (config.window_width, config.window_height)
    recorder.save_schedule(schedule, size)
    return ExperimentManager(schedule, recorder, size)


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_factorial_schedule(config):
    schedule = generate_experiment_trials(config)
    assert schedule == generate_experiment_trials(config)
    assert schedule != generate_experiment_trials(replace(config, random_seed=43))
    assert len(schedule) == 320
    assert Counter(t.condition.direction for t in schedule) == {"left": 160, "right": 160}
    conditions = set(product(config.directions, config.target_widths, config.target_distances))
    for block in range(1, 11):
        group = [t for t in schedule if t.block_number == block]
        assert len(group) == 32
        assert Counter(t.condition.direction for t in group) == {"left": 16, "right": 16}
        assert {(t.condition.direction, t.condition.target_width, t.condition.distance) for t in group} == conditions
        assert [t.trial_number for t in group] == list(range(1, 33))
    assert [t.overall_trial_number for t in schedule] == list(range(1, 321))


def test_circular_boundaries():
    assert circle_contains((3, 4), (0, 0), 5)
    assert circle_contains((0, 0), (0, 0), 5)
    assert not circle_contains((4, 4), (0, 0), 5)
    assert not circle_contains((5.01, 0), (0, 0), 5)
    assert Trial("right", 40, 250).circle(1280, 800) == ((890, 400), 20)
    with pytest.raises(ValueError):
        Trial("left", 80, 700).circle(1280, 800)


def test_measurements_misses_and_raw_clicks(tmp_path, config):
    manager = make_manager(tmp_path, config)
    assert not manager.click((1, 1), 0)
    assert manager.start((640, 400), 1_000_000_000)
    manager.motion((643, 404), 1_010_000_000)
    assert not manager.click((646, 408), 1_020_000_000)
    target, _ = manager.current.condition.circle(*manager.window_size)
    assert manager.click(target, 1_100_000_000)
    folder = manager.recorder.folder
    trial = read_csv(folder / "trials.csv")[0]
    assert float(trial["movement_time_ms"]) == 100
    from math import dist
    assert float(trial["path_length_px"]) == pytest.approx(10 + dist((646, 408), target))
    assert trial["miss_count"] == "1"
    assert trial["total_clicks"] == "2"
    events = read_csv(folder / "mouse_events.csv")
    assert events[0]["event_type"] == "center_start"
    assert events[0]["relative_time_ms"] == "0.0"
    assert len(read_csv(folder / "clicks.csv")) == 2
    assert events[-1]["x"] == str(target[0])
    assert trial["status"] == "completed"


@pytest.mark.parametrize("age", [-1, 0, 121, True, 24.5, "20"])
def test_invalid_age(age):
    with pytest.raises(ValueError):
        Demographics("id", age, COMPUTER_HOURS[0], "Left")


def test_demographics_serialization_and_participant_isolation(tmp_path, config):
    first = make_recorder(tmp_path, config, "first")
    second = make_recorder(tmp_path, config, "second")
    first.save_onboarding(Demographics("first", 24, COMPUTER_HOURS[2], "Left", "Right"), {"participant_id": "first"})
    row = read_csv(first.folder / "demographics.csv")[0]
    assert row["age"] == "24" and row["mouse_hand"] == "Left" and row["dominant_hand"] == "Right"
    assert read_csv(second.folder / "demographics.csv")[0]["age"] == ""
    assert first.folder != second.folder
    with pytest.raises(ValueError, match="participant mismatch"):
        second.save_onboarding(Demographics("first", None, COMPUTER_HOURS[-1], "Left"), {"participant_id": "first"})


def test_consent_required(tmp_path, config):
    folder = tmp_path / "participant_unconsented"
    folder.mkdir()
    (folder / "consent.json").write_text(json.dumps({"participant_id": "unconsented", "consented": False}))
    with pytest.raises(PermissionError):
        Recorder(folder, "unconsented", asdict(config))
    assert not (folder / "demographics.csv").exists()
    pygame.init()
    try:
        app = Application(config, data_path=tmp_path)
        app.transition(AppState.CONSENT)
        with pytest.raises(PermissionError):
            app.transition(AppState.DEMOGRAPHICS)
        assert app.manager is None
    finally:
        pygame.quit()


def test_fixed_trackpad_context_has_no_machine_information():
    assert fixed_input_metadata("id", (1280, 800)) == dict(
        participant_id="id", input_device="Trackpad", window_width=1280, window_height=800)


def test_interruption_preserves_completed_and_active_data(tmp_path, config):
    manager = make_manager(tmp_path, config)
    manager.start(manager.center, 0)
    manager.click(manager.current.condition.circle(*manager.window_size)[0], 20_000_000)
    manager.start(manager.center, 100_000_000)
    manager.click((0, 0), 110_000_000)
    manager.stop("withdrawn")
    rows = read_csv(manager.recorder.folder / "trials.csv")
    assert len(rows) == 2
    assert rows[0]["status"] == "completed" and rows[1]["status"] == "interrupted"
    assert rows[1]["success"] == "False" and rows[1]["miss_count"] == "1"
    assert manager.recorder.session["status"] == "withdrawn"
    with pytest.raises(RuntimeError, match="immutable"):
        manager.recorder.checkpoint({})


def test_crash_recovery_is_separate_and_keeps_schedule(tmp_path, config):
    manager = make_manager(tmp_path, config)
    manager.start(manager.center, 0)
    manager.click(manager.current.condition.circle(*manager.window_size)[0], 10_000_000)
    manager.start(manager.center, 20_000_000)
    manager.motion((644, 403), 40_000_000)
    manager.checkpoint(2_000_000_000)
    source = manager.recorder.folder
    original = (source / "mouse_events.csv").read_bytes()
    # Simulate a partially appended CSV. Recovery trusts durable transactions.
    with (source / "trials.csv").open("a") as handle:
        handle.write("partial,")
    recover_session(source, tmp_path / "recovered")
    recovered = tmp_path / "recovered"
    assert (source / "mouse_events.csv").read_bytes() == original
    assert (source / "trial_sequence.csv").read_bytes() == (recovered / "trial_sequence.csv").read_bytes()
    rows = read_csv(recovered / "trials.csv")
    assert len(rows) == 2 and rows[1]["status"] == "interrupted"
    assert float(rows[1]["path_length_px"]) == 5
    assert json.loads((recovered / "session.json").read_text())["status"] == "incomplete"


def test_full_320_trials_export_and_offline_analysis(tmp_path, config):
    manager = make_manager(tmp_path, config)
    for number in range(320):
        if manager.on_break:
            assert number % 32 == 0
            manager.on_break = False
        assert manager.start(manager.center, number * 1_000_000_000)
        manager.click(manager.current.condition.circle(*manager.window_size)[0], number * 1_000_000_000 + 100_000_000)
    assert manager.finished and manager.recorder.finalized
    assert manager.recorder.session["total_active_movement_time_ms"] == 32000
    folder = manager.recorder.folder
    assert len(read_csv(folder / "trials.csv")) == 320
    assert len(read_csv(folder / "clicks.csv")) == 320
    assert len(read_csv(folder / "mouse_events.csv")) == 640
    from fitts.analysis.statistics import analyze, load_session, validate_completed_session
    session, frames = load_session(folder)
    assert validate_completed_session(session, frames)
    output = tmp_path / "analysis"
    analyze(folder, output)
    assert len(read_csv(output / "per_condition.csv")) == 32
    assert (output / "movement_time_vs_difficulty.png").exists()
    frames["trials"].loc[0, "status"] = "interrupted"
    with pytest.raises(ValueError):
        validate_completed_session(session, frames)


def test_application_workflow_and_focus_loss(tmp_path, config):
    pygame.init()
    try:
        app = Application(config, data_path=tmp_path)
        app.transition(AppState.CONSENT)
        consent = app.screens[AppState.CONSENT]
        consent.checked = True
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=consent._layout()[2].rect.center))
        assert app.machine.state is AppState.DEMOGRAPHICS
        demographics = app.screens[AppState.DEMOGRAPHICS]
        demographics.values.update(age="30", computer_hours_per_week=COMPUTER_HOURS[0], mouse_hand="Right")
        def forward(form):
            app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=form.buttons()[1].rect.center))
        forward(demographics)
        assert app.machine.state is AppState.INSTRUCTIONS
        info = read_csv(app.recorder.folder / "device_info.csv")[0]
        assert info["input_device"] == "Trackpad"
        assert info["os_name"] == "" and info["cpu_model"] == ""
        app.transition(AppState.PRACTICE)
        # Exercise real practice, which must write no experimental measurements.
        practice = app.screens[AppState.PRACTICE]
        from fitts.core.practice_engine import PracticePhase
        while practice.engine.phase is not PracticePhase.COMPLETE:
            practice.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=practice._center_rect().center))
            practice.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=practice._target_rect().center))
        assert not read_csv(app.recorder.folder / "trials.csv")
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=practice._experiment_button().rect.center))
        assert app.machine.state is AppState.EXPERIMENT
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=app.manager.center))
        app.screens[AppState.EXPERIMENT].render()
        app.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        assert app.machine.state is AppState.ABORTED
        assert app.recorder.session["status"] == "incomplete"
        assert read_csv(app.recorder.folder / "trials.csv")[0]["status"] == "interrupted"
        app.screens[AppState.ABORTED].render()
    finally:
        pygame.quit()
