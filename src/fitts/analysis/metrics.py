"""Pure measurement helpers for offline recomputation."""

import math


def shannon_id(distance, width):
    if distance <= 0 or width <= 0:
        raise ValueError("Distance and width must be positive")
    return math.log2(distance / width + 1)


def path_length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))
