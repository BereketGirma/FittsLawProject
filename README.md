# Fitts' Law Experiment

A Python/Pygame desktop application for a controlled study of horizontal pointing movements. This phase provides pseudonymous participant onboarding, draft consent, task instructions, and a functional practice session. The 320-trial recorded experiment and analysis pipeline are intentionally reserved for a later phase.

## Requirements

- Python 3.11 or newer
- A desktop environment capable of opening a Pygame window

## Setup and installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Launch

```bash
python -m fitts.main
```

The default window is 1280 × 800 at 60 FPS. Window size, target dimensions and distances, random seed, and practice count are read from `config/experiment.json` and validated at startup. Press Escape or close the window to leave at any stage.

## Workflow

1. Review the study overview on the welcome screen.
2. Read the scrollable draft consent document. Continuing is disabled until the checkbox is selected.
3. Review the task instructions and left/center/right diagram.
4. Complete practice trials by clicking the center start box, then the active target.
5. Review the practice completion summary or repeat practice.

Only affirmative consent creates `data/<participant_id>/consent.json`. Declining or exiting during onboarding writes no participant record. Practice remains separate from the future 320 official trials and does not record mouse trajectories.

The consent wording in `docs/consent_template.md` is explicitly a draft. Replace it with institution-approved text and contact details before collecting data.

## Repository architecture

```text
config/                 Experiment configuration
data/                   Ignored participant records (.gitkeep only in Git)
docs/                   Consent draft and study documentation
src/fitts/main.py       Pygame initialization and single application loop
src/fitts/core/         Configuration, state, trial geometry, and practice logic
src/fitts/data/         Consent persistence and future recording modules
src/fitts/ui/           Screens, shared controls, and visual theme
src/fitts/analysis/     Reserved offline analysis modules
test/                   Automated tests
```

## Tests

```bash
SDL_VIDEODRIVER=dummy python -m pytest
```

The tests use Pygame's dummy video driver, so they do not require participant interaction or a visible window.
