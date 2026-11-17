# Experiment protocol

## Consent and workflow

WELCOME → CONSENT → DEMOGRAPHICS → INSTRUCTIONS → PRACTICE → EXPERIMENT ↔ BREAK → COMPLETE.

Escape permits withdrawal at every screen; closing the window terminates participation. No participant folder or recorded input is written before affirmative consent. A UUID participant code stays constant, with a separate UUID session ID. Consent version class-project-1 describes a student group project, using data to compare trackpad pointing speed/accuracy by target size, distance and direction. No payment or other compensation is provided. Estimated full duration is 15–20 minutes including instructions, practice and short breaks, depending on pace and break duration. Participants can ask the group member running the activity questions before agreeing.

Demographics ask optional age (integer 1–120, blank to decline), “Approximately how many hours per week do you use a computer?” (Less than 5 hours; 5–10 hours; 11–20 hours; 21–40 hours; More than 40 hours; Prefer not to answer), and “Which hand will you use on the trackpad during this activity?” (Left or Right). Dominant hand is separately optional (Left, Right, Ambidextrous, Prefer not to answer). Operating and dominant hand are independent. The age range is a plausibility check only.

Everyone uses the same computer and trackpad. There is no device-review step or system-specification collection. The fixed input type Trackpad and application window dimensions are retained solely as task context; legacy machine-specification columns remain blank. No OS/CPU/RAM/software/display specifications, DPI, hostnames, usernames, network data or persistent hardware identifiers are queried. Demographics can be reviewed through Back before recorded trials and are saved when Continue is selected.

## Allocation and geometry

Default conditions: left/right; widths 20, 40, 60, 80 pixels; center-to-center distances 150, 250, 350, 450 pixels. Ten repetitions mean ten complete factorial blocks. Each block includes every direction/width/distance combination once: 32 trials, 16 per direction. Overall: 320 tasks, 160 per direction.

A local `random.Random(random_seed)` shuffles a fresh copy of the complete condition list for each block. The generator advances across blocks and is not reseeded per block. Default seed is 42; participants share the configured seed unless changed by the researcher. Seed, configuration and actual order/target centers are saved before collection. An existing schedule cannot be regenerated.

Start circle radius is 30 pixels. Destination diameter is configured width; its center is nominal distance left/right of window center, with fixed vertical alignment. Configuration rejects clipped/overlapping circles, duplicate conditions, odd diameters, invalid seeds and disabling required recording. The window freezes at the pre-experiment size (default 1280×800), or native-resolution fullscreen, during trials. Windows per-monitor DPI awareness is set before display initialization to prevent bitmap scaling, and text uses regular/bold UI fonts rendered at native pixels. Geometry uses application pixels, not calibrated physical distances. The legacy target_height remains for rectangle geometry compatibility; it does not set circle size.

## Timing, hits, errors and paths

1. Waiting for center: only a left-button click inside/on the green circle starts the trial. The cursor is never automatically moved.
2. Start: capture actual click coordinates and `time.perf_counter_ns()` and activate one destination. This is a center_start event, excluded from destination attempts/errors.
3. Active trial: retain every captured Pygame MOUSEMOTION and MOUSEBUTTONDOWN event. Timestamps are event processing times rather than hardware times. The 60 FPS event loop drains the queue; rendering, OS scheduling and periodic persistence can contribute latency.
4. Circle hit: `(x-cx)^2+(y-cy)^2 <= radius^2`. The drawing and hit region use the same radius. Only a left-button hit completes a task. Other button-downs count as misses, even a secondary-button click inside the circle. Button numbers remain recorded. Releases and wheel-only MOUSEWHEEL events are not selection attempts.
5. Misses: increment miss_count for each unsuccessful destination attempt. Allow repeated attempts until hit. Keep all clicks and one summary per started task, not one trial per attempt.
6. Duration: `(end_time_ns-start_time_ns)/1e6` milliseconds. Keep both raw timestamps. Returning to center, practice, onboarding and breaks are excluded. Session total active time sums completed durations; interrupted durations are null and excluded.
7. Path: sum Euclidean distance between consecutive recorded positions, including start, motions, miss clicks and final click. No interpolation is performed. Event sampling/coalescing may underestimate physical movement. Store nominal target distance separately.

Practice has ten trials by default, can be repeated, uses circular geometry and saves no experimental trajectories. Start Experiment is separate from Practice Again and Review Instructions. Review permits returning through instructions to demographic review.

## Breaks and interruption

After each 32-trial block except the last, show a participant-controlled break. Continue requires an explicit click and is disabled for one second to avoid accidental progression. Break time is excluded from movement. The legacy break_every key is now 32; block boundaries determine breaks regardless of that key.

Escape dismisses an open dropdown first; otherwise it finalizes status withdrawn. Closing the window finalizes incomplete. Losing keyboard/window focus during official tasks or breaks ends incomplete and displays an incomplete summary. An active task is retained with status interrupted, success=False, null end/duration and all captured events/clicks. Completed tasks remain unchanged. Unstarted tasks produce no fabricated result rows. No session is labeled completed without all successful tasks.

## Persistence and recovery

At start and approximately every second, atomically replace an active-trial checkpoint. At trial completion, sync an atomic journal transaction before appending and syncing mouse, click and trial CSV batches. Update session metadata atomically. Disk errors stop the experiment and show an error; successful persistence is never claimed after failure. Event CSVs are append-only during collection and application-immutable after finalization. Only demographic/input-context snapshots may be replaced during pre-experiment review.

For abnormal exit, stop the source application and run:

```text
python -m fitts.data.recorder SOURCE_FOLDER NEW_OUTPUT_FOLDER
```

Recovery reconstructs consistent CSVs from the journal and latest active checkpoint; committed transactions supersede stale checkpoints. It retains a durably committed successful task exactly once even if CSV appending failed. Source bytes and saved schedule remain unchanged. Recovery always produces an incomplete/finalized export, does not resume or rerandomize blocks, and never fabricates tasks. Sudden failure can lose the events since the last checkpoint (approximately one second under normal conditions).

After 320 successes and successful final persistence, show total/left/right counts, misses, active movement time, participant ID and a saved confirmation. No statistical regression occurs in the app.

## Offline analysis

```text
python -m fitts.analysis.statistics data/participant_ID --output analysis_output/ID
```

The analysis extra supplies Pandas, NumPy and Matplotlib. Validate finalized completion, identities, assigned/actual counts, exact schedule, each factorial block, durations, trajectory sums and click/error counts. Reject incomplete sessions. Write per-condition means and paths, total/average errors, Shannon ID `log2(A/W+1)`, direction comparisons and two PNG plots to a new directory. Raw CSVs are never overwritten. Practice is absent from official measurement files. Statistical interpretation follows the study's analysis plan.
