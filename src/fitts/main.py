"""Pygame entry point for the Fitts' Law experiment."""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import pygame

from fitts.core.config import ConfigurationError, ExperimentConfig, load_config
from fitts.core.state import AppState, ParticipantSession, StateMachine
from fitts.data.consent import ConsentRecord, ConsentStore
from fitts.ui import theme
from fitts.ui.consent import ConsentScreen
from fitts.ui.instructions import InstructionsScreen
from fitts.ui.practice import PracticeScreen
from fitts.ui.welcome import WelcomeScreen
from fitts.ui.demographics import DemographicsScreen
from fitts.core.device_info import fixed_input_metadata
from fitts.core.display import enable_native_dpi
from fitts.ui.experiment import ExperimentScreen
from fitts.ui.completion import CompletionScreen
from fitts.core.experiment_manager import ExperimentManager
from fitts.core.trial_generator import generate_experiment_trials
from fitts.data.recorder import Recorder

FPS = 60
WINDOW_TITLE = "Fitts' Law Experiment"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "experiment.json"
CONSENT_DOCUMENT_PATH = PROJECT_ROOT / "docs" / "consent_template.md"
DATA_PATH = PROJECT_ROOT / "data"


class Application:
    """Own the session, screen objects, and the application's only event loop."""

    def __init__(
        self,
        config: ExperimentConfig,
        *,
        data_path: str | Path = DATA_PATH,
        consent_document_path: str | Path = CONSENT_DOCUMENT_PATH,
    ) -> None:
        self.config = config
        self.machine = StateMachine()
        self.session = ParticipantSession()
        self.recorder = None
        self.manager = None
        self.persistence_error = None
        self.consent_store = ConsentStore(data_path)
        flags = pygame.FULLSCREEN if config.fullscreen else pygame.RESIZABLE
        size = pygame.display.get_desktop_sizes()[0] if config.fullscreen else (config.window_width, config.window_height)
        self.screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption(WINDOW_TITLE)
        self.fonts = theme.fonts()
        self.running = True
        self.clock = pygame.time.Clock()
        self.screens = {
            AppState.WELCOME: WelcomeScreen(self.screen, self.fonts, self.session.participant_id),
            AppState.CONSENT: ConsentScreen(
                self.screen, self.fonts, self.session.participant_id, consent_document_path
            ),
            AppState.INSTRUCTIONS: InstructionsScreen(self.screen, self.fonts, self.session.participant_id),
            AppState.PRACTICE: PracticeScreen(self.screen, self.fonts, self.session.participant_id, config),
            AppState.DEMOGRAPHICS: DemographicsScreen(self.screen, self.fonts, self.session.participant_id),
        }

    def transition(self, destination: AppState) -> None:
        if destination in {AppState.DEMOGRAPHICS, AppState.INSTRUCTIONS, AppState.PRACTICE, AppState.EXPERIMENT} and not self.session.has_consented:
            raise PermissionError("Consent is required")
        self.machine.transition(destination)

    def _abort(self, status="withdrawn") -> None:
        if self.manager:
            self.manager.stop(status)
        elif self.recorder and not self.recorder.finalized:
            self.recorder.finalize(status)
        if self.machine.state not in {AppState.COMPLETE, AppState.ABORTED}:
            self.transition(AppState.ABORTED)
        self.running = False

    def _resize(self, event: pygame.event.Event) -> None:
        if self.manager:
            return  # Recorded geometry must remain identical to the saved schedule.
        # The configured minimum guarantees every configured target remains visible.
        size = (max(event.w, self.config.window_width), max(event.h, self.config.window_height))
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        for screen in self.screens.values():
            screen.screen = self.screen

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.persistence_error:
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False
            return
        try:
            self._handle_event(event)
        except (OSError, ValueError, RuntimeError) as exc:
            self.persistence_error = str(exc)

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._abort("incomplete")
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            current_screen = self.screens[self.machine.state]
            if getattr(current_screen, "open_index", None) is not None:
                current_screen.handle_event(event)
                return
            self._abort()
            return
        focus_lost = event.type == pygame.WINDOWFOCUSLOST or (event.type == pygame.ACTIVEEVENT and getattr(event, "gain", 1) == 0 and getattr(event, "state", 0) & 2)
        if focus_lost and self.manager and not self.recorder.finalized:
            self.manager.stop("incomplete")
            self._show_summary()
            return
        if event.type == pygame.VIDEORESIZE and not self.config.fullscreen:
            self._resize(event)
            return

        action = self.screens[self.machine.state].handle_event(event)
        if action in {"exit", "decline"}:
            self._abort()
        elif self.machine.state is AppState.WELCOME and action == "continue":
            self.transition(AppState.CONSENT)
        elif self.machine.state is AppState.CONSENT and action == "agree":
            if not self.session.has_consented:
                record = ConsentRecord.affirmative(self.session.participant_id, "class-project-1")
                self.consent_store.save(record)
                self.session.has_consented = True
                self.recorder = Recorder(self.consent_store.path_for(self.session.participant_id).parent,
                                         self.session.participant_id, asdict(self.config))
            self.transition(AppState.DEMOGRAPHICS)
        elif self.machine.state is AppState.DEMOGRAPHICS:
            if action == "back":
                self.transition(AppState.CONSENT)
            elif action == "continue":
                self.recorder.save_onboarding(self.screens[AppState.DEMOGRAPHICS].response(),
                                             fixed_input_metadata(self.session.participant_id, self.screen.get_size()))
                self.transition(AppState.INSTRUCTIONS)
        elif self.machine.state is AppState.INSTRUCTIONS and action == "back":
            self.transition(AppState.DEMOGRAPHICS)
        elif self.machine.state is AppState.INSTRUCTIONS and action == "start":
            self.screens[AppState.PRACTICE].reset()
            self.transition(AppState.PRACTICE)
        elif self.machine.state is AppState.PRACTICE and action == "back":
            self.transition(AppState.INSTRUCTIONS)
        elif self.machine.state is AppState.PRACTICE and action == "experiment":
            self._start_experiment()
        elif self.machine.state is AppState.EXPERIMENT and action == "break":
            self.transition(AppState.BREAK)
        elif self.machine.state is AppState.BREAK and action == "resume":
            self.transition(AppState.EXPERIMENT)
        elif self.machine.state is AppState.EXPERIMENT and action == "complete":
            self._show_summary()

    def _start_experiment(self):
        if not self.session.has_consented or not self.recorder:
            raise PermissionError("Consent is required")
        # Freeze the current window before saving schedule geometry and device metadata.
        size = self.screen.get_size()
        self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN if self.config.fullscreen else 0)
        for screen in self.screens.values():
            screen.screen = self.screen
        self.recorder.save_onboarding(self.screens[AppState.DEMOGRAPHICS].response(),
                                     fixed_input_metadata(self.session.participant_id, size))
        schedule = generate_experiment_trials(self.config)
        self.recorder.save_schedule(schedule, size)
        self.manager = ExperimentManager(schedule, self.recorder, size)
        screen = ExperimentScreen(self.screen, self.fonts, self.session.participant_id, self.manager)
        self.screens[AppState.EXPERIMENT] = self.screens[AppState.BREAK] = screen
        self.transition(AppState.EXPERIMENT)

    def _show_summary(self):
        if not self.recorder.finalized:
            raise RuntimeError("Cannot confirm persistence before finalization")
        destination = AppState.COMPLETE if self.recorder.session["status"] == "completed" else AppState.ABORTED
        self.transition(destination)
        self.screens[destination] = CompletionScreen(self.screen, self.fonts, self.session.participant_id, self.recorder.session)

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            if not self.running:
                break
            if self.manager and not self.persistence_error:
                try:
                    self.manager.checkpoint()
                except OSError as exc:
                    self.persistence_error = str(exc)
            if self.persistence_error:
                from fitts.ui.components import draw_wrapped
                self.screen.fill(theme.BACKGROUND)
                draw_wrapped(self.screen, "Saving failed. The experiment has stopped. " + self.persistence_error,
                             self.fonts["body"], theme.DANGER, 50, 100, self.screen.get_width() - 100)
                draw_wrapped(self.screen, "Do not treat this session as complete. Use the documented recovery command on the session folder. Press Escape to exit.",
                             self.fonts["body"], theme.TEXT, 50, 260, self.screen.get_width() - 100)
            else:
                self.screens[self.machine.state].render()
            pygame.display.flip()
            self.clock.tick(FPS)


def main() -> int:
    try:
        config = load_config(DEFAULT_CONFIG_PATH)
    except ConfigurationError as exc:
        print(f"Unable to start {WINDOW_TITLE}: {exc}", file=sys.stderr)
        return 2

    enable_native_dpi()
    pygame.init()
    try:
        Application(config).run()
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
