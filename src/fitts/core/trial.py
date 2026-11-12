"""Reusable pointing-trial definitions and geometry."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Trial:
    direction: str
    target_width: int
    distance: int

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
