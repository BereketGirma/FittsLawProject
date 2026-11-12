"""Pygame entry point for the Fitts' Law experiment."""

from __future__ import annotations

import sys
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
        self.consent_store = ConsentStore(data_path)
        flags = pygame.FULLSCREEN if config.fullscreen else pygame.RESIZABLE
        self.screen = pygame.display.set_mode((config.window_width, config.window_height), flags)
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
        }

    def transition(self, destination: AppState) -> None:
        self.machine.transition(destination)

    def _abort(self) -> None:
        if self.machine.state not in {AppState.COMPLETE, AppState.ABORTED}:
            self.transition(AppState.ABORTED)
        self.running = False

    def _resize(self, event: pygame.event.Event) -> None:
        # The configured minimum guarantees every configured target remains visible.
        size = (max(event.w, self.config.window_width), max(event.h, self.config.window_height))
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        for screen in self.screens.values():
            screen.screen = self.screen

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._abort()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._abort()
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
                record = ConsentRecord.affirmative(self.session.participant_id, "draft-1")
                self.consent_store.save(record)
                self.session.has_consented = True
            self.transition(AppState.INSTRUCTIONS)
        elif self.machine.state is AppState.INSTRUCTIONS and action == "back":
            self.transition(AppState.CONSENT)
        elif self.machine.state is AppState.INSTRUCTIONS and action == "start":
            self.screens[AppState.PRACTICE].reset()
            self.transition(AppState.PRACTICE)
        elif self.machine.state is AppState.PRACTICE and action == "back":
            self.transition(AppState.INSTRUCTIONS)

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            if not self.running:
                break
            self.screens[self.machine.state].render()
            pygame.display.flip()
            self.clock.tick(FPS)


def main() -> int:
    try:
        config = load_config(DEFAULT_CONFIG_PATH)
    except ConfigurationError as exc:
        print(f"Unable to start {WINDOW_TITLE}: {exc}", file=sys.stderr)
        return 2

    pygame.init()
    try:
        Application(config).run()
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
