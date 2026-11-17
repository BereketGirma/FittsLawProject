"""Persistence-confirmed completion and incomplete-session summaries."""

import pygame

from fitts.ui import theme
from fitts.ui.components import Button, draw_footer


class CompletionScreen:
    def __init__(self, screen, fonts, participant_id, session):
        self.screen, self.fonts, self.participant_id, self.session = screen, fonts, participant_id, session

    def button(self):
        return Button(pygame.Rect(self.screen.get_width() // 2 - 90, self.screen.get_height() - 130, 180, 52), "Exit")

    def handle_event(self, event):
        return "exit" if self.button().clicked(event) else None

    def render(self):
        self.screen.fill(theme.BACKGROUND)
        session = self.session
        complete = session["status"] == "completed"
        lines = [("Experiment Completed!" if complete else "Session ended — experiment incomplete"),
                 "Thank you for participating.",
                 f"Total completed trials: {session['completed_trials']}"]
        if complete:
            lines += [f"Left Trials: {session['completed_trials'] // 2}    Right Trials: {session['completed_trials'] // 2}"]
        lines += [f"Total missed clicks: {session['total_missed_clicks']}",
                  f"Total active movement time: {session['total_active_movement_time_ms'] / 1000:.3f} seconds",
                  f"Participant ID: {self.participant_id}",
                  "Your responses have been saved successfully."]
        for i, line in enumerate(lines):
            label = self.fonts["heading" if i == 0 else "body"].render(line, True, theme.SUCCESS if i == 0 and complete else theme.TEXT)
            self.screen.blit(label, label.get_rect(center=(self.screen.get_width() // 2, 130 + i * 58)))
        self.button().draw(self.screen, self.fonts["button"])
        draw_footer(self.screen, self.fonts["small"], self.participant_id)
