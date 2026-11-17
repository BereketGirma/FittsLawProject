"""Participant form with explicit text inputs and expandable dropdown menus."""

import pygame

from fitts.data.models import COMPUTER_HOURS, Demographics
from fitts.ui import theme
from fitts.ui.components import Button, draw_footer, draw_wrapped


class FormScreen:
    title = ""
    OPTION_HEIGHT = 44

    def __init__(self, screen, fonts, participant_id):
        self.screen, self.fonts, self.participant_id = screen, fonts, participant_id
        self.values = {}
        self.fields = []
        self.active = None
        self.open_index = None
        self.highlighted = 0
        self.error = ""
        self.field_y = 170

    def field_rect(self, index):
        return pygame.Rect(self.screen.get_width() // 2, self.field_y + index * 100,
                           self.screen.get_width() // 2 - 70, 54)

    def menu_rect(self):
        rect = self.field_rect(self.open_index)
        height = len(self.fields[self.open_index][2]) * self.OPTION_HEIGHT
        y = rect.bottom + 6
        if y + height > self.screen.get_height() - 125:
            y = rect.top - height - 6
        return pygame.Rect(rect.x, y, rect.width, height)

    def buttons(self):
        w, h = self.screen.get_size()
        return (Button(pygame.Rect(60, h - 95, 140, 50), "Back", secondary=True),
                Button(pygame.Rect(w - 240, h - 95, 180, 50), "Continue"))

    def validate(self):
        raise NotImplementedError

    def open_menu(self, index):
        self.open_index = self.active = index
        key, _, options = self.fields[index]
        value = self.values.get(key)
        self.highlighted = options.index(value) if value in options else 0

    def handle_event(self, event):
        if self.open_index is not None:
            key, _, options = self.fields[self.open_index]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                menu = self.menu_rect()
                if menu.collidepoint(event.pos):
                    self.values[key] = options[(event.pos[1] - menu.y) // self.OPTION_HEIGHT]
                    self.open_index = None
                    return None
                self.open_index = None
                # Consume the dismissal so it cannot accidentally submit the form.
                return None
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    step = -1 if event.key == pygame.K_UP else 1
                    self.highlighted = (self.highlighted + step) % len(options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.values[key] = options[self.highlighted]
                    self.open_index = None
                elif event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                    self.open_index = None
                return None
        back, forward = self.buttons()
        if back.clicked(event):
            return "back"
        if forward.clicked(event):
            try:
                self.validate()
                self.error = ""
                return "continue"
            except ValueError as exc:
                self.error = str(exc)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = None
            for i, (_, _, options) in enumerate(self.fields):
                if self.field_rect(i).collidepoint(event.pos):
                    self.active = i
                    if options:
                        self.open_menu(i)
                    break
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                step = -1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1
                self.active = (self.active + step) % len(self.fields) if self.active is not None else (len(self.fields) - 1 if step < 0 else 0)
            elif self.active is not None:
                key, _, options = self.fields[self.active]
                if options and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_DOWN, pygame.K_UP):
                    self.open_menu(self.active)
                elif not options:
                    value = self.values.get(key, "")
                    character = getattr(event, "unicode", "")
                    if event.key == pygame.K_BACKSPACE:
                        self.values[key] = value[:-1]
                    elif character and character in "0123456789" and len(value) < 3:
                        self.values[key] = value + character
        return None

    def render(self):
        self.screen.fill(theme.BACKGROUND)
        self.screen.blit(self.fonts["title"].render(self.title, True, theme.TEXT), (60, 40))
        self.screen.blit(self.fonts["small"].render("Click a field to type, or open a dropdown to choose an answer. Tab moves between fields.", True, theme.MUTED), (60, 108))
        for i, (key, label, options) in enumerate(self.fields):
            rect = self.field_rect(i)
            focused = i == self.active
            draw_wrapped(self.screen, label, self.fonts["body"], theme.TEXT, 60, rect.y + 4, rect.x - 85, 2)
            pygame.draw.rect(self.screen, theme.INPUT, rect, border_radius=8)
            pygame.draw.rect(self.screen, theme.PRIMARY_HOVER if focused else theme.INPUT_BORDER,
                             rect, 2 if focused else 1, border_radius=8)
            value = self.values.get(key)
            text = str(value) if value not in (None, "") else ("Select an option" if options else "e.g. 21")
            text_surface = self.fonts["body"].render(text, True, theme.TEXT if value not in (None, "") else theme.MUTED)
            self.screen.blit(text_surface, (rect.x + 16, rect.y + 10))
            if options:
                cx, cy = rect.right - 24, rect.centery
                pygame.draw.lines(self.screen, theme.TEXT, False,
                                  [(cx - 6, cy - 3), (cx, cy + 3), (cx + 6, cy - 3)], 2)
                hint = "Choose one option"
            else:
                hint = "Type your age in years, or leave blank to skip"
                if focused and pygame.time.get_ticks() % 1000 < 500:
                    caret_x = rect.x + 16 + (text_surface.get_width() if value else 0)
                    pygame.draw.line(self.screen, theme.TEXT, (caret_x, rect.y + 13), (caret_x, rect.bottom - 13), 2)
            self.screen.blit(self.fonts["small"].render(hint, True, theme.MUTED), (rect.x, rect.bottom + 6))
        if self.error:
            self.screen.blit(self.fonts["small"].render(self.error, True, theme.DANGER), (60, self.screen.get_height() - 140))
        for button in self.buttons():
            button.draw(self.screen, self.fonts["button"])
        draw_footer(self.screen, self.fonts["small"], self.participant_id)
        # Draw menus last so options appear above the fields underneath them.
        if self.open_index is not None:
            menu = self.menu_rect()
            key, _, options = self.fields[self.open_index]
            pygame.draw.rect(self.screen, theme.SURFACE, menu.inflate(4, 4), border_radius=8)
            pygame.draw.rect(self.screen, theme.INPUT_BORDER, menu.inflate(4, 4), 1, border_radius=8)
            for i, option in enumerate(options):
                row = pygame.Rect(menu.x, menu.y + i * self.OPTION_HEIGHT, menu.width, self.OPTION_HEIGHT)
                if row.collidepoint(pygame.mouse.get_pos()) or i == self.highlighted:
                    pygame.draw.rect(self.screen, theme.SURFACE_HOVER, row)
                if option == self.values.get(key):
                    pygame.draw.rect(self.screen, theme.PRIMARY, (row.x, row.y + 6, 3, row.height - 12))
                label = self.fonts["body"].render(option, True, theme.TEXT)
                self.screen.blit(label, (row.x + 16, row.y + 7))


class DemographicsScreen(FormScreen):
    title = "About your computer use"

    def __init__(self, screen, fonts, participant_id):
        super().__init__(screen, fonts, participant_id)
        self.fields = [("age", "Age (optional)", None),
                       ("computer_hours_per_week", "Approximately how many hours per week do you use a computer?", COMPUTER_HOURS),
                       ("mouse_hand", "Which hand will you use on the trackpad during this activity?", ("Left", "Right")),
                       ("dominant_hand", "Dominant hand (optional)", ("Prefer not to answer", "Left", "Right", "Ambidextrous"))]
        self.values = dict(age="", computer_hours_per_week=None, mouse_hand=None, dominant_hand="Prefer not to answer")

    def response(self):
        age = self.values["age"]
        return Demographics(self.participant_id, int(age) if age else None,
                            self.values["computer_hours_per_week"], self.values["mouse_hand"],
                            None if self.values["dominant_hand"] == "Prefer not to answer" else self.values["dominant_hand"])

    def validate(self):
        self.response()
