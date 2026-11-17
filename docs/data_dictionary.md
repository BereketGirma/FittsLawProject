# Data dictionary

CSVs use UTF-8, headers, Python csv and newline-safe writing. Null fields are blank; booleans are True/False. Coordinates, widths and distances use Pygame pixels (origin top-left). Nanosecond timestamps are monotonic processing-clock readings, not calendar time. Relative times/durations are milliseconds. Data lives under data/participant_<id>/.

## consent.json and session.json

consent.json: participant_id, consent_version, consented (affirmative only), UTC ISO-8601 timestamp. Current version: class-project-1 (class group project, no compensation, estimated 15–20 minutes). Created before response/measurement storage.

session.json: participant_id, session_id, created_at, config snapshot, random_seed, status (onboarding/running/completed/incomplete/withdrawn), finalized, completed_trials, total_missed_clicks, total_active_movement_time_ms, focus_policy, clock description, checkpoint_interval_seconds. After review: demographics/device_info snapshots. At schedule creation: assigned_trials and started_at. Finalization adds ended_at; recovery adds recovered_at. Dates are UTC ISO-8601. Active movement total sums successful completed trials only.

## demographics.csv

```csv
participant_id,age,computer_hours_per_week,mouse_hand,dominant_hand
```

age: integer 1–120, blank if declined; no birth date. computer_hours_per_week: Less than 5 hours; 5–10 hours; 11–20 hours; 21–40 hours; More than 40 hours; Prefer not to answer. mouse_hand: Left/Right for operating the trackpad (historical column name retained). dominant_hand: independently Left/Right/Ambidextrous or blank if declined. One response row; header-only if onboarding ended before review.

## device_info.csv

```csv
participant_id,os_name,os_version,cpu_model,cpu_architecture,cpu_count,ram_gb,python_version,pygame_version,display_width,display_height,window_width,window_height,display_scale,refresh_rate_hz,input_device,mouse_dpi
```

All participants use the same machine and trackpad. Only participant_id, input_device (always Trackpad), window_width and window_height are populated for current sessions. Window dimensions are necessary to interpret task coordinates. All historical OS, CPU, RAM, Python/Pygame version, display, scaling, refresh-rate and mouse-DPI columns remain blank for export compatibility; no machine-specification collector runs. Existing historical sessions remain untouched.

## trial_sequence.csv

```csv
participant_id,block_number,trial_number,overall_trial_number,direction,target_width_px,target_distance_px,target_center_x,target_center_y
```

Actual assigned schedule saved before official input. Default block_number 1–10; trial_number 1–32 within block; overall_trial_number 1–320. direction left/right. Width is circle diameter (20/40/60/80); distance is center-to-center horizontal distance (150/250/350/450). Target centers are fixed window coordinates. Each condition appears once per block. Presence of an assigned row does not imply task completion.

## trials.csv

```csv
participant_id,session_id,block_number,trial_number,overall_trial_number,direction,target_width_px,target_distance_px,start_x,start_y,target_x,target_y,start_time_ns,end_time_ns,movement_time_ms,path_length_px,miss_count,total_clicks,success,status
```

One row per started task, exactly 320 completed rows for the default completed study. An interrupted session may include a final interrupted row. Unstarted tasks have no result rows. start_x/y are the actual start-click coordinates within radius 30. target_x/y are the target center, not the final cursor click (available in raw clicks/events).

start_time_ns/end_time_ns: monotonic start/hit timestamps. movement_time_ms: start-to-hit duration, null if interrupted. path_length_px: Euclidean path through recorded start, motions, intermediate click and final hit positions (or last captured point for interrupted tasks). miss_count: unsuccessful destination attempts. total_clicks: all destination attempts, including final success, excluding center start. success True only on left-button target hit; status completed/interrupted. Session status separately distinguishes withdrawal and incomplete completion.

## mouse_events.csv

```csv
participant_id,session_id,block_number,trial_number,event_type,timestamp_ns,relative_time_ms,x,y,direction,button
```

event_type: center_start, motion or destination_click. Start has relative_time_ms 0 and never counts as a destination attempt. Each motion/click retains processing timestamp and coordinates. direction identifies task condition. button is the Pygame number for destination clicks, blank for start/motion. Extra direction/button columns supplement the requested base schema. Only active official trials generate rows, not practice, breaks, onboarding or returns to center.

## clicks.csv

```csv
participant_id,session_id,block_number,trial_number,timestamp_ns,relative_time_ms,click_x,click_y,hit_target,click_number,button
```

One row per destination button-down, including all misses. hit_target requires left button and a point inside/on the circle. click_number is 1-based within task; button retains Pygame button number (1=left). Releases and wheel-only events are excluded. Center-start clicks are identifiable exclusively in mouse_events.csv and absent here.

## Journal and recovery

journal/trial_NNNN.json: durable authoritative transaction containing trial/events/clicks, written before CSV append. journal/active.json: latest atomic active checkpoint, written at start and about every second. A committed transaction supersedes a stale checkpoint for the same task. Recovery reconstructs a new incomplete/finalized export without changing source bytes or the actual schedule. Keep journals under the same retention policy as pseudonymous raw CSVs.

## Derived analysis output

A separate new output directory contains derived_trials.csv (official completed rows plus index_of_difficulty), per_condition.csv (direction/width/distance/difficulty, trial_count, mean_movement_time_ms, average_path_length_px, total_errors, average_errors), left_vs_right.csv (direction statistics), summary.csv (participant ID, trials/errors, average errors/path and total active time), movement_time_vs_difficulty.png and left_vs_right.png. Shannon difficulty is log2(A/W+1). The command rejects incomplete/inconsistent sessions and never overwrites raw CSVs. Practice is excluded.
