import json

import pytest

from fitts.core.config import ConfigurationError, load_config


def test_loads_repository_configuration():
    config = load_config("config/experiment.json")
    assert (config.window_width, config.window_height) == (1280, 800)
    assert config.official_trial_count == 320
    assert config.practice_trials == 10


def test_rejects_missing_configuration_values(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"experiment": {"name": "incomplete"}}), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="missing configuration keys"):
        load_config(path)


def test_rejects_targets_outside_window(tmp_path):
    source = json.loads(open("config/experiment.json", encoding="utf-8").read())
    source["experiment"]["target_distances"] = [700]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="horizontal window boundary"):
        load_config(path)
