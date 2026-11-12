"""Trial generation shared by practice and the future formal experiment."""

from __future__ import annotations

import itertools
import random

from fitts.core.config import ExperimentConfig
from fitts.core.trial import Trial


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
