"""UI-independent official experiment lifecycle and measurement rules."""

from __future__ import annotations

import time

from fitts.core.mouse_tracker import MouseTracker
from fitts.core.trial import circle_contains


class ExperimentManager:
    START_RADIUS = 30

    def __init__(self, schedule, recorder, window_size):
        if not schedule:
            raise ValueError("Schedule cannot be empty")
        self.schedule, self.recorder, self.window_size = schedule, recorder, window_size
        self.index = 0
        self.tracker = None
        self.clicks = []
        self.misses = 0
        self.on_break = False
        self.finished = False
        self.last_checkpoint = 0
        self.start_position = None

    @property
    def current(self):
        return self.schedule[self.index]

    @property
    def center(self):
        return self.window_size[0] // 2, self.window_size[1] // 2

    def start(self, position, timestamp_ns=None):
        if self.tracker or self.on_break or self.finished or not circle_contains(position, self.center, self.START_RADIUS):
            return False
        context = {key: self.recorder.session[key] for key in ("participant_id", "session_id")}
        context.update(block_number=self.current.block_number, trial_number=self.current.trial_number,
                       direction=self.current.condition.direction)
        self.tracker = MouseTracker(context, position, timestamp_ns)
        self.start_position = position
        self.clicks, self.misses = [], 0
        self.last_checkpoint = self.tracker.start_time_ns
        self.recorder.checkpoint(self.transaction("interrupted"))
        return True

    def motion(self, position, timestamp_ns=None):
        if self.tracker:
            self.tracker.add("motion", position, timestamp_ns)

    def click(self, position, timestamp_ns=None, button=1):
        if not self.tracker:
            return self.start(position, timestamp_ns) if button == 1 else False
        center, radius = self.current.condition.circle(*self.window_size)
        hit = button == 1 and circle_contains(position, center, radius)
        event = self.tracker.add("destination_click", position, timestamp_ns)
        event["button"] = button
        self.clicks.append(dict(self.tracker.context, timestamp_ns=event["timestamp_ns"],
                               relative_time_ms=event["relative_time_ms"], click_x=position[0], click_y=position[1],
                               hit_target=hit, click_number=len(self.clicks) + 1, button=button))
        if not hit:
            self.misses += 1
            return False
        self.recorder.commit(self.transaction("completed", event["timestamp_ns"]))
        self.tracker = None
        self.index += 1
        if self.index == len(self.schedule):
            self.recorder.finalize("completed")
            self.finished = True
        elif self.schedule[self.index].block_number != self.schedule[self.index - 1].block_number:
            self.on_break = True
        return True

    def transaction(self, status, end_time_ns=None):
        assigned, tracker = self.current, self.tracker
        target, _ = assigned.condition.circle(*self.window_size)
        row = dict(tracker.context, overall_trial_number=assigned.overall_trial_number,
                   target_width_px=assigned.condition.target_width, target_distance_px=assigned.condition.distance,
                   start_x=self.start_position[0], start_y=self.start_position[1], target_x=target[0], target_y=target[1],
                   start_time_ns=tracker.start_time_ns, end_time_ns=end_time_ns,
                   movement_time_ms=(end_time_ns - tracker.start_time_ns) / 1_000_000 if end_time_ns is not None else None,
                   path_length_px=tracker.path_length_px, miss_count=self.misses, total_clicks=len(self.clicks),
                   success=status == "completed", status=status)
        return {"trial": row, "events": tracker.events, "clicks": self.clicks}

    def checkpoint(self, now_ns=None):
        now_ns = time.perf_counter_ns() if now_ns is None else now_ns
        if self.tracker and now_ns - self.last_checkpoint >= 1_000_000_000:
            self.recorder.checkpoint(self.transaction("interrupted"))
            self.last_checkpoint = now_ns

    def stop(self, status="withdrawn"):
        if self.recorder.finalized:
            return
        if self.tracker:
            self.recorder.commit(self.transaction("interrupted"))
            self.tracker = None
        self.recorder.finalize(status)
