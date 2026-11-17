"""Reusable pointing-trial definitions and geometry."""

from dataclasses import dataclass


def circle_contains(point: tuple[float, float], center: tuple[float, float], radius: float) -> bool:
    return (point[0] - center[0]) ** 2 + (point[1] - center[1]) ** 2 <= radius ** 2


@dataclass(frozen=True, slots=True)
class Trial:
    direction: str
    target_width: int
    distance: int

    def circle(self, window_width: int, window_height: int) -> tuple[tuple[int, int], float]:
        if self.direction not in {"left", "right"}:
            raise ValueError("invalid direction")
        center = (window_width // 2 + (-self.distance if self.direction == "left" else self.distance), window_height // 2)
        radius = self.target_width / 2
        if (center[0] - radius < 0 or center[0] + radius > window_width
                or center[1] - radius < 0 or center[1] + radius > window_height):
            raise ValueError("destination circle does not fit window")
        return center, radius

    def target_coordinates(
        self, window_width: int, window_height: int, target_height: int
    ) -> tuple[int, int, int, int]:
        """Return target x, y, width, height using center-to-center distance."""
        if self.direction not in {"left", "right"}:
            raise ValueError(f"unsupported direction: {self.direction}")
        center_x = window_width / 2
        target_center_x = center_x + (-self.distance if self.direction == "left" else self.distance)
        x = round(target_center_x - self.target_width / 2)
        y = round(window_height / 2 - target_height / 2)
        if x < 0 or x + self.target_width > window_width or y < 0 or y + target_height > window_height:
            raise ValueError("target does not fit inside the window")
        return x, y, self.target_width, target_height
