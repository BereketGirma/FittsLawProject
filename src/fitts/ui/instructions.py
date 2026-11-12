"""Participant instructions and task diagram."""

import pygame

from fitts.ui import theme
from fitts.ui.components import Button, draw_footer


STEPS = (
    "Start each trial by clicking the box in the center of the screen.",
    "A target will appear either to the left or right.",
    "Move your mouse horizontally toward the target.",
    "Click the target as quickly and accurately as possible.",
    "Return to the center to begin the next trial.",
    "Target sizes and distances will change.",
    "The experiment contains 320 trials: 160 left and 160 right.",
    "Breaks will be provided throughout the activity.",
    "You may stop participation at any time.",
)


class InstructionsScreen:
    def __init__(self, screen: pygame.Surface, app_fonts: dict[str, pygame.font.Font], participant_id: str) -> None:
        self.screen, self.fonts, self.participant_id = screen, app_fonts, participant_id

    def _buttons(self) -> tuple[Button, Button]:
        width, height = self.screen.get_size()
        return (
            Button(pygame.Rect(60, height - 94, 140, 52), "Back", secondary=True),
            Button(pygame.Rect(width - 260, height - 94, 200, 52), "Start Practice"),
        )

    def handle_event(self, event: pygame.event.Event) -> str | None:
        back, start = self._buttons()
        if back.clicked(event):
            return "back"
        if start.clicked(event):
            return "start"
        return None

    def render(self) -> None:
        self.screen.fill(theme.BACKGROUND)
        width, height = self.screen.get_size()
        margin = max(40, min(70, width // 14))
        self.screen.blit(self.fonts["title"].render("How the experiment works", True, theme.TEXT), (margin, 42))
        diagram = pygame.Rect(width - 390, 135, 320, 145)
        pygame.draw.rect(self.screen, theme.SURFACE, diagram, border_radius=14)
        cy = diagram.centery
        pygame.draw.line(self.screen, theme.BORDER, (diagram.x + 40, cy), (diagram.right - 40, cy), 3)
        for cx, color in ((diagram.x + 50, theme.PRIMARY), (diagram.centerx, theme.SUCCESS), (diagram.right - 50, theme.PRIMARY)):
            pygame.draw.rect(self.screen, color, pygame.Rect(cx - 18, cy - 28, 36, 56), border_radius=5)
        center_label = self.fonts["small"].render("left target       start       right target", True, theme.MUTED)
        self.screen.blit(center_label, center_label.get_rect(center=(diagram.centerx, diagram.bottom - 18)))

        y = 125
        available_width = max(420, width - 500)
        for number, step in enumerate(STEPS, start=1):
            circle_center = (margin + 14, y + 12)
            pygame.draw.circle(self.screen, theme.SURFACE_HOVER, circle_center, 14)
            number_label = self.fonts["small"].render(str(number), True, theme.TEXT)
            self.screen.blit(number_label, number_label.get_rect(center=circle_center))
            text = self.fonts["body"].render(step, True, theme.TEXT)
            self.screen.blit(text, (margin + 42, y))
            y += 48
        if height >= 760:
            note = self.fonts["small"].render("Practice trials are separate from the 320 recorded trials.", True, theme.SUCCESS)
            self.screen.blit(note, (margin, height - 135))
        back, start = self._buttons()
        back.draw(self.screen, self.fonts["button"])
        start.draw(self.screen, self.fonts["button"])
        draw_footer(self.screen, self.fonts["small"], self.participant_id)
