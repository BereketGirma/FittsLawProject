"""Small reusable Pygame controls and text helpers."""

from __future__ import annotations

import pygame

from fitts.ui import theme


class Button:
    def __init__(self, rect: pygame.Rect, label: str, *, enabled: bool = True, secondary: bool = False) -> None:
        self.rect = rect
        self.label = label
        self.enabled = enabled
        self.secondary = secondary

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        hovered = self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())
        if not self.enabled:
            color = theme.DISABLED
        elif self.secondary:
            color = theme.SURFACE_HOVER if hovered else theme.SURFACE
        else:
            color = theme.PRIMARY_HOVER if hovered else theme.PRIMARY
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        if self.secondary:
            pygame.draw.rect(surface, theme.BORDER, self.rect, width=1, border_radius=10)
        label = font.render(self.label, True, theme.TEXT if self.enabled else theme.MUTED)
        surface.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event: pygame.event.Event) -> bool:
        return (
            self.enabled
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    line = words[0]
    for word in words[1:]:
        candidate = f"{line} {word}"
        if font.size(candidate)[0] <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def draw_wrapped(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    x: int,
    y: int,
    max_width: int,
    line_gap: int = 6,
) -> int:
    line_height = font.get_linesize() + line_gap
    for line in wrap_text(text, font, max_width):
        surface.blit(font.render(line, True, color), (x, y))
        y += line_height
    return y


def draw_footer(surface: pygame.Surface, font: pygame.font.Font, participant_id: str) -> None:
    label = font.render(f"Session: {participant_id[:12]}", True, theme.MUTED)
    surface.blit(label, (32, surface.get_height() - 28))
