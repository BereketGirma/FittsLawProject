"""Shared colors and font construction."""

import pygame

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


def fonts() -> dict[str, pygame.font.Font]:
    return {
        "title": pygame.font.SysFont("Arial", 42, bold=True),
        "heading": pygame.font.SysFont("Arial", 28, bold=True),
        "body": pygame.font.SysFont("Arial", 20),
        "body_bold": pygame.font.SysFont("Arial", 20, bold=True),
        "small": pygame.font.SysFont("Arial", 16),
        "button": pygame.font.SysFont("Arial", 18, bold=True),
    }
