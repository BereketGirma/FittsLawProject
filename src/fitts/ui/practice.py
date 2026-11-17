"""Functional practice task using the reusable practice engine."""

import pygame

from fitts.core.config import ExperimentConfig
from fitts.core.practice_engine import PracticeEngine, PracticePhase
from fitts.core.trial_generator import generate_practice_trials
from fitts.core.trial import circle_contains
from fitts.ui import theme
from fitts.ui.components import Button, draw_footer


class PracticeScreen:
    FEEDBACK_MS = 650

    def __init__(self, screen: pygame.Surface, app_fonts: dict[str, pygame.font.Font], participant_id: str, config: ExperimentConfig) -> None:
        self.screen, self.fonts, self.participant_id, self.config = screen, app_fonts, participant_id, config
        self.feedback: tuple[str, tuple[int, int, int]] | None = None
        self.feedback_until = 0
        self.reset()

    def reset(self) -> None:
        self.engine = PracticeEngine(generate_practice_trials(self.config))
        self.feedback = None
        if not self.config.require_center_click:
            self.engine.activate_target()

    def _center_rect(self) -> pygame.Rect:
        width, height = self.screen.get_size()
        return pygame.Rect(width // 2 - 30, height // 2 - 30, 60, 60)

    def _target_rect(self) -> pygame.Rect:
        center, radius = self.engine.current_trial.circle(*self.screen.get_size())
        return pygame.Rect(center[0] - radius, center[1] - radius, radius * 2, radius * 2)

    def _completion_buttons(self) -> tuple[Button, Button]:
        width, height = self.screen.get_size()
        return (
            Button(pygame.Rect(width // 2 - 225, height // 2 + 90, 200, 54), "Practice Again", secondary=True),
            Button(pygame.Rect(width // 2 + 25, height // 2 + 90, 200, 54), "Review Instructions"),
        )

    def _experiment_button(self) -> Button:
        width, height = self.screen.get_size()
        return Button(pygame.Rect(width // 2 - 120, height // 2 + 160, 240, 54), "Start Experiment")

    def _set_feedback(self, message: str, color: tuple[int, int, int]) -> None:
        self.feedback = (message, color)
        self.feedback_until = pygame.time.get_ticks() + self.FEEDBACK_MS

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.engine.phase is PracticePhase.COMPLETE:
            if self._experiment_button().clicked(event):
                return "experiment"
            again, back = self._completion_buttons()
            if again.clicked(event):
                self.reset()
            elif back.clicked(event):
                return "back"
            return None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        if self.engine.phase is PracticePhase.WAITING_FOR_CENTER:
            if circle_contains(event.pos, self._center_rect().center, 30):
                self.engine.activate_target()
                self._set_feedback("Target active — move horizontally and click it", theme.SUCCESS)
            else:
                self._set_feedback("Click the center circle to begin", theme.DANGER)
        else:
            hit = circle_contains(event.pos, self._target_rect().center, self.engine.current_trial.target_width / 2)
            result = self.engine.target_click(hit)
            if result.hit:
                self._set_feedback("Hit!", theme.SUCCESS)
                if self.engine.phase is not PracticePhase.COMPLETE and not self.config.require_center_click:
                    self.engine.activate_target()
            else:
                self._set_feedback("Miss — try the active target again", theme.DANGER)
        return None

    def render(self) -> None:
        self.screen.fill(theme.BACKGROUND)
        width, height = self.screen.get_size()
        if self.engine.phase is PracticePhase.COMPLETE:
            self._render_complete()
            return
        progress = self.fonts["body_bold"].render(
            f"Practice  •  Trial {self.engine.index + 1} / {len(self.engine.trials)}", True, theme.TEXT
        )
        self.screen.blit(progress, (42, 38))
        misses = self.fonts["small"].render(f"Misses: {self.engine.misses}", True, theme.MUTED)
        self.screen.blit(misses, (width - misses.get_width() - 42, 43))
        center = self._center_rect()
        center_color = theme.SUCCESS if self.engine.phase is PracticePhase.WAITING_FOR_CENTER else theme.SURFACE
        pygame.draw.circle(self.screen, center_color, center.center, 30)
        center_label = self.fonts["small"].render("START", True, theme.BACKGROUND if self.engine.phase is PracticePhase.WAITING_FOR_CENTER else theme.MUTED)
        self.screen.blit(center_label, center_label.get_rect(center=center.center))
        if self.engine.phase is PracticePhase.TARGET_ACTIVE:
            target = self._target_rect()
            pygame.draw.circle(self.screen, theme.PRIMARY, target.center, target.width // 2)
        instruction = "Click the center circle" if self.engine.phase is PracticePhase.WAITING_FOR_CENTER else "Click the blue target"
        prompt = self.fonts["heading"].render(instruction, True, theme.TEXT)
        self.screen.blit(prompt, prompt.get_rect(center=(width // 2, 120)))
        if self.feedback and pygame.time.get_ticks() <= self.feedback_until:
            message, color = self.feedback
            rendered = self.fonts["body"].render(message, True, color)
            self.screen.blit(rendered, rendered.get_rect(center=(width // 2, height - 100)))
        draw_footer(self.screen, self.fonts["small"], self.participant_id)

    def _render_complete(self) -> None:
        width, height = self.screen.get_size()
        title = self.fonts["title"].render("Practice complete", True, theme.SUCCESS)
        self.screen.blit(title, title.get_rect(center=(width // 2, height // 2 - 100)))
        detail = self.fonts["body"].render(
            f"You completed {len(self.engine.trials)} practice trials with {self.engine.misses} missed clicks.",
            True, theme.TEXT,
        )
        self.screen.blit(detail, detail.get_rect(center=(width // 2, height // 2 - 40)))
        note = self.fonts["small"].render("Ready? Start the recorded experiment, or review your instructions and answers.", True, theme.MUTED)
        self.screen.blit(note, note.get_rect(center=(width // 2, height // 2 + 5)))
        again, back = self._completion_buttons()
        again.draw(self.screen, self.fonts["button"])
        back.draw(self.screen, self.fonts["button"])
        self._experiment_button().draw(self.screen, self.fonts["button"])
        draw_footer(self.screen, self.fonts["small"], self.participant_id)
