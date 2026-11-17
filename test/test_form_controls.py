"""Test explicit selection and text entry rather than hidden click cycling."""

import pygame
import pytest

from fitts.data.models import COMPUTER_HOURS
from fitts.ui.demographics import DemographicsScreen
from fitts.ui import theme


@pytest.fixture
def form():
    pygame.init()
    screen = pygame.display.set_mode((1280, 800))
    yield DemographicsScreen(screen, theme.fonts(), "form-test")
    pygame.quit()


def click(position):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position)


def key(value, character=""):
    return pygame.event.Event(pygame.KEYDOWN, key=value, unicode=character, mod=0)


def test_dropdown_opens_without_choosing_and_selects_clicked_option(form):
    form.handle_event(click(form.field_rect(1).center))
    assert form.open_index == 1
    assert form.values["computer_hours_per_week"] is None
    menu = form.menu_rect()
    form.render()
    form.handle_event(click((menu.x + 20, menu.y + 3 * form.OPTION_HEIGHT + 20)))
    assert form.open_index is None
    assert form.values["computer_hours_per_week"] == COMPUTER_HOURS[3]


def test_dropdown_keyboard_selects_and_escape_cancels(form):
    form.handle_event(key(pygame.K_TAB))  # age
    form.handle_event(key(pygame.K_TAB))  # computer use
    form.handle_event(key(pygame.K_SPACE))
    form.handle_event(key(pygame.K_DOWN))
    assert form.values["computer_hours_per_week"] is None
    form.handle_event(key(pygame.K_RETURN))
    assert form.values["computer_hours_per_week"] == COMPUTER_HOURS[1]
    form.handle_event(key(pygame.K_SPACE))
    form.handle_event(key(pygame.K_DOWN))
    form.handle_event(key(pygame.K_ESCAPE))
    assert form.values["computer_hours_per_week"] == COMPUTER_HOURS[1]


def test_text_input_requires_focus_and_supports_backspace(form):
    form.handle_event(key(pygame.K_2, "2"))
    assert form.values["age"] == ""
    form.handle_event(click(form.field_rect(0).center))
    for character in "24":
        form.handle_event(key(ord(character), character))
    assert form.values["age"] == "24"
    form.handle_event(key(pygame.K_BACKSPACE))
    assert form.values["age"] == "2"
    form.handle_event(key(pygame.K_a, "a"))
    assert form.values["age"] == "2"


def test_menu_dismissal_cannot_accidentally_submit(form):
    form.open_menu(3)
    menu = form.menu_rect()
    assert 0 <= menu.top < menu.bottom <= form.screen.get_height() - 125
    assert form.handle_event(click(form.buttons()[1].rect.center)) is None
    assert form.open_index is None
