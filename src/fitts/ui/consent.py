"""Scrollable consent screen backed by a replaceable Markdown document."""

from pathlib import Path

import pygame

from fitts.ui import theme
from fitts.ui.components import Button, draw_footer, wrap_text


class ConsentScreen:
    def __init__(self, screen: pygame.Surface, app_fonts: dict[str, pygame.font.Font], participant_id: str, document_path: str | Path) -> None:
        self.screen, self.fonts, self.participant_id = screen, app_fonts, participant_id
        self.document = Path(document_path).read_text(encoding="utf-8-sig")
        self.checked = False
        self.scroll_offset = 0
        self.max_scroll = 0

    def _layout(self) -> tuple[pygame.Rect, pygame.Rect, Button, Button]:
        width, height = self.screen.get_size()
        margin = max(30, min(80, width // 12))
        viewport = pygame.Rect(margin, 115, width - margin * 2, max(180, height - 330))
        checkbox = pygame.Rect(margin, height - 174, 26, 26)
        agree = Button(pygame.Rect(width - margin - 220, height - 112, 220, 54), "I Agree / Continue", enabled=self.checked)
        decline = Button(pygame.Rect(margin, height - 112, 150, 54), "Decline", secondary=True)
        return viewport, checkbox, agree, decline

    def handle_event(self, event: pygame.event.Event) -> str | None:
        _, checkbox, agree, decline = self._layout()
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset - event.y * 42))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            label_area = pygame.Rect(checkbox.x, checkbox.y - 5, min(720, self.screen.get_width() - checkbox.x - 20), 38)
            if label_area.collidepoint(event.pos):
                self.checked = not self.checked
            elif agree.clicked(event):
                return "agree"
            elif decline.clicked(event):
                return "decline"
        return None

    def _document_lines(self, max_width: int) -> list[tuple[str, pygame.font.Font, tuple[int, int, int], int]]:
        result = []
        for raw_line in self.document.splitlines():
            line = raw_line.strip()
            if not line:
                result.append(("", self.fonts["body"], theme.TEXT, 14))
                continue
            if line.startswith("# "):
                continue
            if line.startswith("## "):
                text, font, color, gap = line[3:], self.fonts["body_bold"], theme.PRIMARY_HOVER, 12
            else:
                text, font, color, gap = line, self.fonts["body"], theme.TEXT, 7
            result.extend((wrapped, font, color, gap) for wrapped in wrap_text(text, font, max_width))
        return result

    def render(self) -> None:
        self.screen.fill(theme.BACKGROUND)
        width = self.screen.get_width()
        margin = max(30, min(80, width // 12))
        self.screen.blit(self.fonts["title"].render("Participant Consent", True, theme.TEXT), (margin, 45))
        viewport, checkbox, agree, decline = self._layout()
        pygame.draw.rect(self.screen, theme.SURFACE, viewport, border_radius=12)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(viewport.inflate(-28, -22))
        y = viewport.y + 18 - self.scroll_offset
        for text, font, color, gap in self._document_lines(viewport.width - 58):
            if text:
                self.screen.blit(font.render(text, True, color), (viewport.x + 28, y))
                y += font.get_linesize() + gap
            else:
                y += gap
        self.screen.set_clip(old_clip)
        content_height = y + self.scroll_offset - viewport.y
        self.max_scroll = max(0, content_height - viewport.height + 25)
        if self.max_scroll:
            track = pygame.Rect(viewport.right - 8, viewport.y + 8, 4, viewport.height - 16)
            pygame.draw.rect(self.screen, theme.BORDER, track, border_radius=2)
            thumb_height = max(30, round(track.height * viewport.height / max(content_height, viewport.height)))
            thumb_y = track.y + round((track.height - thumb_height) * self.scroll_offset / self.max_scroll)
            pygame.draw.rect(self.screen, theme.PRIMARY, (track.x, thumb_y, track.width, thumb_height), border_radius=2)
        pygame.draw.rect(self.screen, theme.SURFACE, checkbox, border_radius=5)
        pygame.draw.rect(self.screen, theme.PRIMARY if self.checked else theme.BORDER, checkbox, width=2, border_radius=5)
        if self.checked:
            pygame.draw.lines(self.screen, theme.SUCCESS, False, [(checkbox.x + 5, checkbox.y + 13), (checkbox.x + 11, checkbox.y + 20), (checkbox.x + 22, checkbox.y + 6)], 3)
        label = self.fonts["body"].render("I have read this information and voluntarily agree to participate.", True, theme.TEXT)
        self.screen.blit(label, (checkbox.right + 14, checkbox.y + 2))
        agree.enabled = self.checked
        agree.draw(self.screen, self.fonts["button"])
        decline.draw(self.screen, self.fonts["button"])
        draw_footer(self.screen, self.fonts["small"], self.participant_id)
