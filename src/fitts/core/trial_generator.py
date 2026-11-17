"""Trial generation shared by practice and the future formal experiment."""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from fitts.core.config import ExperimentConfig
from fitts.core.trial import Trial


@dataclass(frozen=True, slots=True)
class AssignedTrial:
    block_number: int
    trial_number: int
    overall_trial_number: int
    condition: Trial


def generate_experiment_trials(config: ExperimentConfig) -> list[AssignedTrial]:
    """Shuffle a fresh factorial block using one local, reproducible RNG."""
    conditions = [Trial(d, w, a) for d, w, a in itertools.product(
        config.directions, config.target_widths, config.target_distances)]
    if len(set(conditions)) != len(conditions):
        raise ValueError("experimental conditions must be unique")
    rng = random.Random(config.random_seed)
    schedule = []
    for block in range(1, config.repetitions + 1):
        ordered = conditions.copy()
        rng.shuffle(ordered)
        for number, condition in enumerate(ordered, 1):
            condition.circle(config.window_width, config.window_height)
            schedule.append(AssignedTrial(block, number, len(schedule) + 1, condition))
    return schedule


def generate_practice_trials(config: ExperimentConfig) -> list[Trial]:
    combinations = [
        Trial(direction, width, distance)
        for direction, width, distance in itertools.product(
            config.directions, config.target_widths, config.target_distances
        )
    ]
    randomizer = random.Random(config.random_seed)
    trials: list[Trial] = []
    while len(trials) < config.practice_trials:
        batch = combinations.copy()
        randomizer.shuffle(batch)
        trials.extend(batch)
    trials = trials[: config.practice_trials]

    # Avoid a strongly one-sided short practice when both directions are available.
    if config.practice_trials >= 2 and len({trial.direction for trial in trials}) == 1:
        last = trials[-1]
        opposite = "right" if last.direction == "left" else "left"
        trials[-1] = Trial(opposite, last.target_width, last.distance)
    return trials
