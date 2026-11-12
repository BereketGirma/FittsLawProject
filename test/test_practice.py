import pytest

from fitts.core.config import load_config
from fitts.core.practice_engine import PracticeEngine, PracticePhase
from fitts.core.trial import Trial
from fitts.core.trial_generator import generate_practice_trials


def test_generates_configured_number_of_deterministic_practice_trials():
    config = load_config("config/experiment.json")
    first = generate_practice_trials(config)
    assert first == generate_practice_trials(config)
    assert len(first) == config.practice_trials
    assert {trial.direction for trial in first} == {"left", "right"}


@pytest.mark.parametrize("direction, expected_x", [("left", 370), ("right", 870)])
def test_target_coordinate_calculation(direction, expected_x):
    assert Trial(direction, 40, 250).target_coordinates(1280, 800, 80) == (expected_x, 360, 40, 80)


def test_all_configured_targets_stay_inside_window():
    config = load_config("config/experiment.json")
    for direction in config.directions:
        for width in config.target_widths:
            for distance in config.target_distances:
                x, y, target_width, target_height = Trial(direction, width, distance).target_coordinates(
                    config.window_width, config.window_height, config.target_height
                )
                assert 0 <= x and x + target_width <= config.window_width
                assert 0 <= y and y + target_height <= config.window_height


def test_practice_requires_activation_and_only_advances_on_hit():
    engine = PracticeEngine([Trial("left", 40, 150), Trial("right", 40, 150)])
    assert not engine.target_click(True).advanced
    engine.activate_target()
    assert not engine.target_click(False).advanced
    assert engine.misses == 1
    assert engine.target_click(True).advanced
    assert engine.index == 1
    assert engine.phase is PracticePhase.WAITING_FOR_CENTER
