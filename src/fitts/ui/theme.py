"""Shared colors and font construction."""

import pygame
import os
from pathlib import Path

BACKGROUND = (15, 20, 31)
SURFACE = (25, 32, 47)
SURFACE_HOVER = (35, 44, 62)
TEXT = (242, 245, 250)
MUTED = (167, 177, 194)
PRIMARY = (88, 136, 255)
PRIMARY_HOVER = (111, 154, 255)
DISABLED = (62, 70, 84)
SUCCESS = (67, 201, 137)
DANGER = (235, 104, 104)
BORDER = (66, 77, 96)
INPUT = (36, 46, 65)
INPUT_BORDER = (130, 148, 175)


def fonts() -> dict[str, pygame.font.Font]:
    # SysFont("Arial") can select Arial Narrow; Segoe UI can select its light
    # variant. Use the exact regular/bold files when installed on Windows.
    font_directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    regular, bold = font_directory / "segoeui.ttf", font_directory / "segoeuib.ttf"
    def face(size, *, weight=False):
        path = bold if weight else regular
        if path.is_file():
            return pygame.font.Font(str(path), size)
        return pygame.font.SysFont("DejaVu Sans,Verdana", size, bold=weight)
    return {
        "title": face(42, weight=True),
        "heading": face(28, weight=True),
        "body": face(22),
        "body_bold": face(22, weight=True),
        "small": face(18),
        "button": face(20, weight=True),
    }
