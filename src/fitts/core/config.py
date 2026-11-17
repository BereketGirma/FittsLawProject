"""Configuration loading and validation for the experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """Raised when experiment configuration is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    name: str
    version: str
    window_width: int
    window_height: int
    fullscreen: bool
    directions: tuple[str, ...]
    target_widths: tuple[int, ...]
    target_distances: tuple[int, ...]
    target_height: int
    repetitions: int
    practice_trials: int
    break_every: int
    random_seed: int
    require_center_click: bool
    record_mouse_movement: bool
    record_missed_clicks: bool
    save_format: str

    @property
    def official_trial_count(self) -> int:
        return (
            len(self.directions)
            * len(self.target_widths)
            * len(self.target_distances)
            * self.repetitions
        )


REQUIRED_KEYS = {field.name for field in ExperimentConfig.__dataclass_fields__.values()}


def _positive_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"'{key}' must be a positive integer")
    return value


def _positive_int_tuple(data: dict[str, Any], key: str) -> tuple[int, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigurationError(f"'{key}' must be a non-empty list")
    if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in value):
        raise ConfigurationError(f"all values in '{key}' must be positive integers")
    return tuple(value)


def load_config(path: str | Path) -> ExperimentConfig:
    """Load and validate a JSON experiment configuration."""
    config_path = Path(path)
    try:
        document = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"configuration file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"invalid JSON in {config_path}: {exc.msg}") from exc

    data = document.get("experiment") if isinstance(document, dict) else None
    if not isinstance(data, dict):
        raise ConfigurationError("configuration must contain an 'experiment' object")
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise ConfigurationError(f"missing configuration keys: {', '.join(sorted(missing))}")

    directions = data.get("directions")
    if not isinstance(directions, list) or set(directions) != {"left", "right"} or len(directions) != 2:
        raise ConfigurationError("'directions' must contain exactly 'left' and 'right'")

    for key in ("fullscreen", "require_center_click", "record_mouse_movement", "record_missed_clicks"):
        if not isinstance(data.get(key), bool):
            raise ConfigurationError(f"'{key}' must be a boolean")

    name, version, save_format = data.get("name"), data.get("version"), data.get("save_format")
    if not all(isinstance(value, str) and value.strip() for value in (name, version, save_format)):
        raise ConfigurationError("'name', 'version', and 'save_format' must be non-empty strings")

    width = _positive_int(data, "window_width")
    height = _positive_int(data, "window_height")
    target_height = _positive_int(data, "target_height")
    widths = _positive_int_tuple(data, "target_widths")
    distances = _positive_int_tuple(data, "target_distances")
    if len(set(widths)) != len(widths) or len(set(distances)) != len(distances):
        raise ConfigurationError("target widths and distances must be unique")
    if max(widths) > height or any(w % 2 for w in widths):
        raise ConfigurationError("circle diameters must be even and fit the window height")
    if min(distances) <= 30 + max(widths) / 2:
        raise ConfigurationError("destination circles must not overlap the center start circle")
    if isinstance(data["random_seed"], bool) or not isinstance(data["random_seed"], int):
        raise ConfigurationError("random_seed must be an integer")
    if not all(data[k] for k in ("require_center_click", "record_mouse_movement", "record_missed_clicks")):
        raise ConfigurationError("official experiments require center clicks, mouse tracking and missed clicks")
    if save_format != "csv":
        raise ConfigurationError("save_format must be csv")
    if target_height > height:
        raise ConfigurationError("target height exceeds the window height")
    half_window = width / 2
    if any(distance + target_width / 2 > half_window for distance in distances for target_width in widths):
        raise ConfigurationError("a configured target would extend beyond the horizontal window boundary")

    return ExperimentConfig(
        name=name.strip(),
        version=version.strip(),
        window_width=width,
        window_height=height,
        fullscreen=data["fullscreen"],
        directions=tuple(directions),
        target_widths=widths,
        target_distances=distances,
        target_height=target_height,
        repetitions=_positive_int(data, "repetitions"),
        practice_trials=_positive_int(data, "practice_trials"),
        break_every=_positive_int(data, "break_every"),
        random_seed=data["random_seed"] if isinstance(data["random_seed"], int) else 0,
        require_center_click=data["require_center_click"],
        record_mouse_movement=data["record_mouse_movement"],
        record_missed_clicks=data["record_missed_clicks"],
        save_format=save_format.strip(),
    )
