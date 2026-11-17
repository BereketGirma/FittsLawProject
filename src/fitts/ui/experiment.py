"""Official circular target task. All measurements belong to the manager."""

import pygame

from fitts.ui import theme
from fitts.ui.components import Button, draw_footer


class ExperimentScreen:
    def __init__(self, screen, fonts, participant_id, manager):
        self.screen, self.fonts, self.participant_id, self.manager = screen, fonts, participant_id, manager
        self.break_ready_at = 0

    def continue_button(self):
        return Button(pygame.Rect(self.screen.get_width() // 2 - 110, self.screen.get_height() - 200, 220, 56),
                      "Continue", enabled=pygame.time.get_ticks() >= self.break_ready_at)

    def handle_event(self, event):
        manager = self.manager
        if manager.finished:
            return "complete"
        if manager.on_break:
            if self.continue_button().clicked(event):
                manager.on_break = False
                return "resume"
            return None
        if event.type == pygame.MOUSEMOTION:
            manager.motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            manager.click(event.pos, button=event.button)
            if manager.finished:
                return "complete"
            if manager.on_break:
                self.break_ready_at = pygame.time.get_ticks() + 1000
                return "break"
        return None

    def render(self):
        self.screen.fill(theme.BACKGROUND)
        manager = self.manager
        w, h = self.screen.get_size()
        if manager.on_break:
            block = manager.schedule[manager.index - 1].block_number
            lines = [f"Block {block} of {manager.schedule[-1].block_number} Complete!",
                     f"You have completed {manager.index} of {len(manager.schedule)} trials.",
                     "Take a short break.", "Click Continue when ready."]
            for i, line in enumerate(lines):
                label = self.fonts["heading"].render(line, True, theme.TEXT)
                self.screen.blit(label, label.get_rect(center=(w // 2, 200 + i * 65)))
            self.continue_button().draw(self.screen, self.fonts["button"])
        else:
            current = manager.current
            block_size = sum(t.block_number == current.block_number for t in manager.schedule)
            lines = [f"Block {current.block_number} / {manager.schedule[-1].block_number}",
                     f"Trial {current.trial_number} / {block_size}",
                     f"Overall Progress: {current.overall_trial_number} / {len(manager.schedule)}"]
            for i, line in enumerate(lines):
                self.screen.blit(self.fonts["body"].render(line, True, theme.TEXT), (35, 30 + i * 30))
            if manager.tracker:
                center, radius = current.condition.circle(*manager.window_size)
                pygame.draw.circle(self.screen, theme.PRIMARY, center, int(radius))
                prompt = "Click the blue circle"
            else:
                pygame.draw.circle(self.screen, theme.SUCCESS, manager.center, manager.START_RADIUS)
                prompt = "Click the center circle to begin"
            label = self.fonts["heading"].render(prompt, True, theme.TEXT)
            self.screen.blit(label, label.get_rect(center=(w // 2, 165)))
        self.screen.blit(self.fonts["small"].render("Escape: withdraw    Closing the window ends the session", True, theme.MUTED), (35, h - 60))
        draw_footer(self.screen, self.fonts["small"], self.participant_id)
