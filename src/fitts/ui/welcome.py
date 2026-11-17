"""Welcome screen."""

import pygame

from fitts.ui import theme
from fitts.ui.components import Button, draw_footer, draw_wrapped


class WelcomeScreen:
    def __init__(self, screen: pygame.Surface, app_fonts: dict[str, pygame.font.Font], participant_id: str) -> None:
        self.screen, self.fonts, self.participant_id = screen, app_fonts, participant_id

    def _buttons(self) -> tuple[Button, Button]:
        width, height = self.screen.get_size()
        return (
            Button(pygame.Rect(width // 2 - 105, height - 180, 210, 56), "Continue"),
            Button(pygame.Rect(width // 2 - 105, height - 108, 210, 50), "Exit", secondary=True),
        )

    def handle_event(self, event: pygame.event.Event) -> str | None:
        continue_button, exit_button = self._buttons()
        if continue_button.clicked(event):
            return "continue"
        if exit_button.clicked(event):
            return "exit"
        return None

    def render(self) -> None:
        self.screen.fill(theme.BACKGROUND)
        width, height = self.screen.get_size()
        content_width = min(760, width - 80)
        x = (width - content_width) // 2
        title = self.fonts["title"].render("Fitts' Law Experiment", True, theme.TEXT)
        self.screen.blit(title, title.get_rect(center=(width // 2, max(90, height // 7))))
        subtitle = self.fonts["heading"].render("Trackpad Pointing · Class Group Project", True, theme.PRIMARY_HOVER)
        self.screen.blit(subtitle, subtitle.get_rect(center=(width // 2, max(145, height // 7 + 58))))
        card = pygame.Rect(x, max(205, height // 3 - 25), content_width, 230)
        pygame.draw.rect(self.screen, theme.SURFACE, card, border_radius=16)
        y = draw_wrapped(
            self.screen,
            "Help our group explore how target size and distance affect trackpad pointing. Allow about 15–20 minutes, including practice and short breaks. Participation is voluntary; no payment is provided.",
            self.fonts["body"], theme.TEXT, card.x + 40, card.y + 35, card.width - 80, 8,
        ) + 25
        info = self.fonts["body_bold"].render("320 total trials  •  160 left  •  160 right", True, theme.SUCCESS)
        self.screen.blit(info, info.get_rect(center=(width // 2, y + 16)))
        continue_button, exit_button = self._buttons()
        continue_button.draw(self.screen, self.fonts["button"])
        exit_button.draw(self.screen, self.fonts["button"])
        draw_footer(self.screen, self.fonts["small"], self.participant_id)
