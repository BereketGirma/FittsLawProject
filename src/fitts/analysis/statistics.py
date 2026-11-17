"""Load and validate official exports; generate separate derived summaries.

Usage: python -m fitts.analysis.statistics data/participant_ID --output analysis_output/ID
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_session(folder):
    folder = Path(folder)
    session = json.loads((folder / "session.json").read_text(encoding="utf-8"))
    frames = {name: pd.read_csv(folder / f"{name}.csv", keep_default_na=True)
              for name in ("trials", "trial_sequence", "mouse_events", "clicks")}
    for name, column in (("trials", "success"), ("clicks", "hit_target")):
        if not frames[name][column].empty and not frames[name][column].isin([True, False]).all():
            raise ValueError(f"Invalid boolean values in {name}.{column}")
    return session, frames


def validate_completed_session(session, frames):
    """Reject incomplete, unbalanced or internally inconsistent official exports."""
    trials, sequence = frames["trials"], frames["trial_sequence"]
    config = session["config"]
    expected = len(config["directions"]) * len(config["target_widths"]) * len(config["target_distances"]) * config["repetitions"]
    if session.get("status") != "completed" or not session.get("finalized"):
        raise ValueError("Session is not finalized and completed")
    if len(trials) != expected or len(sequence) != expected or session["completed_trials"] != expected:
        raise ValueError("Wrong number of assigned or completed trials")
    for name, frame in frames.items():
        if not frame.empty and set(frame.participant_id) != {session["participant_id"]}:
            raise ValueError(f"Participant mismatch in {name}")
        if "session_id" in frame and not frame.empty and set(frame.session_id) != {session["session_id"]}:
            raise ValueError(f"Session mismatch in {name}")
    if not trials.success.eq(True).all() or not trials.status.eq("completed").all():
        raise ValueError("Trials include unsuccessful or interrupted tasks")
    task_keys = set(zip(sequence.block_number, sequence.trial_number))
    for name in ("mouse_events", "clicks"):
        if set(zip(frames[name].block_number, frames[name].trial_number)) != task_keys:
            raise ValueError(f"Unexpected or missing task events in {name}")
    if set(sequence.overall_trial_number) != set(range(1, expected + 1)) or sequence.overall_trial_number.duplicated().any():
        raise ValueError("Invalid schedule numbering")
    keys = ["block_number", "trial_number", "overall_trial_number", "direction", "target_width_px", "target_distance_px"]
    if not trials[keys].reset_index(drop=True).equals(sequence[keys].reset_index(drop=True)):
        raise ValueError("Trial results do not match saved schedule")
    from itertools import product
    conditions = set(product(config["directions"], config["target_widths"], config["target_distances"]))
    for block in range(1, config["repetitions"] + 1):
        group = sequence[sequence.block_number == block]
        if len(group) != len(conditions) or set(zip(group.direction, group.target_width_px, group.target_distance_px)) != conditions:
            raise ValueError("Missing or duplicated conditions within block")
        if set(group.trial_number) != set(range(1, len(conditions) + 1)):
            raise ValueError("Invalid within-block numbering")
    duration = (trials.end_time_ns - trials.start_time_ns) / 1_000_000
    if (duration < 0).any() or not np.isfinite(duration).all() or not np.allclose(duration, trials.movement_time_ms):
        raise ValueError("Invalid movement duration")
    from fitts.analysis.metrics import path_length
    from fitts.core.trial import circle_contains
    for row in trials.itertuples():
        events = frames["mouse_events"]
        events = events[(events.block_number == row.block_number) & (events.trial_number == row.trial_number)]
        clicks = frames["clicks"]
        clicks = clicks[(clicks.block_number == row.block_number) & (clicks.trial_number == row.trial_number)]
        if events.empty or events.iloc[0].event_type != "center_start" or events.iloc[-1].event_type != "destination_click":
            raise ValueError("Missing start or final click event")
        if (events.timestamp_ns.diff().dropna() < 0).any():
            raise ValueError("Nonmonotonic event timestamps")
        if int(events.iloc[0].timestamp_ns) != row.start_time_ns or int(events.iloc[-1].timestamp_ns) != row.end_time_ns:
            raise ValueError("Event timing does not match trial")
        if not np.isclose(path_length(list(zip(events.x, events.y))), row.path_length_px):
            raise ValueError("Path length does not match raw events")
        if len(clicks) != row.total_clicks or clicks.empty or clicks.iloc[-1].hit_target != True or int((~clicks.hit_target.astype(bool)).sum()) != row.miss_count:
            raise ValueError("Click/error counts do not match raw attempts")
        if not events.event_type.isin(["center_start", "motion", "destination_click"]).all() or events.event_type.eq("center_start").sum() != 1:
            raise ValueError("Invalid mouse event types")
        if not np.allclose(events.relative_time_ms, (events.timestamp_ns - row.start_time_ns) / 1_000_000):
            raise ValueError("Invalid relative event times")
        if list(clicks.click_number) != list(range(1, len(clicks) + 1)) or clicks.hit_target.sum() != 1:
            raise ValueError("Invalid click sequence")
        destination_events = events[events.event_type == "destination_click"]
        if (len(destination_events) != len(clicks)
                or list(destination_events.timestamp_ns) != list(clicks.timestamp_ns)
                or list(destination_events.x) != list(clicks.click_x)
                or list(destination_events.y) != list(clicks.click_y)):
            raise ValueError("Click events differ between raw exports")
        for click in clicks.itertuples():
            hit = click.button == 1 and circle_contains((click.click_x, click.click_y), (row.target_x, row.target_y), row.target_width_px / 2)
            if hit != click.hit_target:
                raise ValueError("Recorded hit disagrees with circular geometry")
    return True


def summarize(trials):
    valid = trials[(trials.status == "completed") & trials.success.eq(True)].copy()
    valid["index_of_difficulty"] = np.log2(valid.target_distance_px / valid.target_width_px + 1)
    aggregations = dict(trial_count=("movement_time_ms", "size"),
                        mean_movement_time_ms=("movement_time_ms", "mean"),
                        average_path_length_px=("path_length_px", "mean"),
                        total_errors=("miss_count", "sum"), average_errors=("miss_count", "mean"))
    conditions = valid.groupby(["direction", "target_width_px", "target_distance_px", "index_of_difficulty"]).agg(**aggregations).reset_index()
    directions = valid.groupby("direction").agg(**aggregations).reset_index()
    return valid, conditions, directions


def analyze(folder, output):
    session, frames = load_session(folder)
    validate_completed_session(session, frames)
    # A new directory avoids overwriting either raw data or previous analyses.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    trials, conditions, directions = summarize(frames["trials"])
    trials.to_csv(output / "derived_trials.csv", index=False)
    conditions.to_csv(output / "per_condition.csv", index=False)
    directions.to_csv(output / "left_vs_right.csv", index=False)
    pd.DataFrame([dict(participant_id=session["participant_id"], total_trials=len(trials),
                       total_errors=int(trials.miss_count.sum()), average_errors=trials.miss_count.mean(),
                       average_path_length_px=trials.path_length_px.mean(),
                       total_active_movement_time_ms=trials.movement_time_ms.sum())]).to_csv(output / "summary.csv", index=False)
    from fitts.analysis.plots import plot_conditions
    plot_conditions(conditions, directions, output)


def main():
    parser = argparse.ArgumentParser(description="Validate and analyze a completed Fitts experiment")
    parser.add_argument("session", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.session, args.output)


if __name__ == "__main__":
    main()
