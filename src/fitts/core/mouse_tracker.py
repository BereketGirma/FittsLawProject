"""Event-based trajectory measurement using a monotonic nanosecond clock."""

import math
import time


class MouseTracker:
    def __init__(self, context: dict, start: tuple[int, int], timestamp_ns: int | None = None):
        self.context = context
        self.start_time_ns = time.perf_counter_ns() if timestamp_ns is None else timestamp_ns
        self.last = start
        self.path_length_px = 0.0
        self.events = []
        self.add("center_start", start, self.start_time_ns)

    def add(self, event_type: str, position: tuple[int, int], timestamp_ns: int | None = None) -> dict:
        timestamp_ns = time.perf_counter_ns() if timestamp_ns is None else timestamp_ns
        if timestamp_ns < self.start_time_ns or (self.events and timestamp_ns < self.events[-1]["timestamp_ns"]):
            raise ValueError("mouse timestamps must be monotonic")
        self.path_length_px += math.dist(self.last, position)
        self.last = position
        row = dict(self.context, event_type=event_type, timestamp_ns=timestamp_ns,
                   relative_time_ms=(timestamp_ns - self.start_time_ns) / 1_000_000,
                   x=position[0], y=position[1])
        self.events.append(row)
        return row
