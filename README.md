# Fitts' Law Experiment

Python/Pygame desktop research application with circular targets: ten independently randomized blocks of 32 tasks, **320 recorded trials, 160 left and 160 right**. Practice is excluded from recorded data.

## Install and launch

Requires Python 3.11+ and a desktop display. Use the existing project environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,analysis]"
python -m fitts.main
```

For a new environment, first run `python -m venv .venv`. On macOS/Linux activate with `source .venv/bin/activate`. The installed `fitts-experiment` command also launches the app. Use the source checkout with an editable installation: configuration and consent assets live beside `src/`.

## Participant workflow

Welcome → consent → demographics → instructions → practice → ten experimental blocks with breaks → saved completion summary.

This class group project uses the same computer and trackpad for everyone. Allow approximately 15–20 minutes including instructions, practice and short breaks; actual time depends on pace and breaks. No payment is provided. Demographics collect optional integer age (1–120; blank declines), weekly computer-use category, trackpad operating hand and optional dominant hand. Machine specifications and mouse DPI are not collected, and there is no device-information screen. Review/change responses through Back buttons before starting recorded trials. Numeric inputs show a typing hint and caret. Click a dropdown to show its options, then click an answer or use arrow keys and Enter. Tab moves between fields; Escape dismisses an open dropdown before a second Escape withdraws.

Click the green center circle, then the blue destination circle as quickly and accurately as possible. Every miss remains recorded; the target stays active until hit. Return the cursor manually to center. The window becomes fixed-size during recorded trials. Continue on each block break requires an explicit click after a one-second guard.

Escape withdraws; closing the window ends incomplete. Switching away during the recorded experiment also ends incomplete, preserving the active task as interrupted. No incomplete session is shown as completed.

The consent explains the class project, intended data use, estimated time, no compensation, voluntary participation, breaks and local data storage. Participants can ask the group member running the activity questions before agreeing. Its version is `class-project-1`. The age range is a plausibility check, not an eligibility decision.

## Data and durability

Only affirmative consent creates `data/participant_<id>/`. Names, emails, birth dates, hostnames, usernames, serial numbers, MAC/IP addresses and other persistent identifiers are not collected. Each launch creates a new random participant ID; existing sessions are never overwritten.

```text
data/participant_<id>/
  consent.json
  demographics.csv
  device_info.csv
  session.json
  trial_sequence.csv
  trials.csv
  mouse_events.csv
  clicks.csv
  journal/                 # Durable transactions and active checkpoint
```

UTF-8 CSVs include headers and blank nulls. The seed, config, actual schedule, response snapshots, status and totals are saved. Trial-end CSV batches and journal transactions are flushed and synced. The active trial is checkpointed approximately every second; motion events stay buffered between checkpoints. Completion is displayed only after final persistence succeeds. Saving errors stop interaction and show an error screen.

After a crash or saving error, stop the source app and recover into a **new** directory:

```powershell
python -m fitts.data.recorder data/participant_ID data/recovered_ID
```

Recovery rebuilds CSVs from durable transactions and the latest active checkpoint, ignoring partially appended CSV rows. Source bytes remain unchanged. Recovered exports are marked incomplete/finalized. Abrupt failure can lose uncheckpointed events (roughly one second under normal conditions). Interrupted sessions are not resumed; their exact randomized schedules remain preserved and no missing tasks are invented. Finalized sessions reject further application writes.

## Measurements and analysis

Movement time runs from the successful center-start click to the successful left-button destination click using `time.perf_counter_ns()`. Actual cursor path length sums Euclidean distances over the start, captured motion/click positions and final hit. Nominal target distance is separate. Recorded Pygame events do not capture every physical movement; timestamps reflect processing time and event-loop latency. Windows DPI awareness avoids blurry OS bitmap scaling, and fonts use explicit regular/bold faces. Fullscreen uses the native desktop resolution. Targets retain their configured pixel sizes. The device CSV retains its historical columns for compatibility; machine fields are blank, with only the fixed Trackpad input and task window geometry saved.

```powershell
python -m fitts.analysis.statistics data/participant_ID --output analysis_output/ID
```

Analysis validates completed sessions before producing per-condition means, path lengths, error summaries, left/right comparisons, Shannon difficulty `log2(A/W+1)` and PNG plots. Incomplete sessions are rejected. Output must be a new directory. Derived results never overwrite raw CSVs. `data/` and `analysis_output/` are ignored by Git.

## Tests and architecture

```powershell
python -m pytest
```

Tests use dummy video/audio drivers and deterministic events, including a full 320-trial session, consent gating, interruptions, partial-write recovery and offline plots. Check real mouse/display behavior on study hardware before deployment.

`main.py` owns one event loop; `ui/` renders screens; `core/` implements configuration, geometry, schedule and measurements; `data/` manages consent, responses and durable CSV exports; `analysis/` operates offline. See [protocol](docs/experiment_protocol.md) and [data dictionary](docs/data_dictionary.md).
