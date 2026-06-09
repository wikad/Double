import math
import os
import sys
import time

import pygame


WIDTH = 1100
HEIGHT = 720
FPS = 60
HEADER_HEIGHT = 118

BG = (244, 247, 250)
INK = (28, 35, 43)
MUTED = (103, 113, 125)
PANEL = (255, 255, 255)
ACCENT = (35, 134, 214)
GOOD = (37, 149, 96)
BAD = (198, 64, 64)
LINE = (213, 220, 228)


class GUI:
    def __init__(self, client):
        pygame.init()
        self.client = client
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Double")
        self.clock = pygame.time.Clock()
        self.fonts = {
            "title": pygame.font.SysFont("Arial", 38, bold=True),
            "h2": pygame.font.SysFont("Arial", 25, bold=True),
            "body": pygame.font.SysFont("Arial", 19),
            "small": pygame.font.SysFont("Arial", 16),
        }
        self.symbols = self._load_symbols()
        self.click_targets = []
        self.action_buttons = {}
        self.auto_reconnecting = False
        self.running = True

    def run(self):
        while self.running:
            snapshot = self.client.snapshot()
            if snapshot["round_reset_pending"] and not snapshot["is_connected"]:
                self._restart_game()
                snapshot = self.client.snapshot()
            self._handle_events(snapshot)
            self._draw(snapshot)
            pygame.display.flip()
            self.clock.tick(FPS)

        self.close()

    def _handle_events(self, snapshot):
        self.click_targets = self.click_targets[:]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r and self._can_restart(snapshot):
                    self._restart_game()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos, snapshot)

    def _handle_click(self, pos, snapshot):
        if self._can_restart(snapshot):
            restart_button = self.action_buttons.get("restart")
            if restart_button and restart_button.collidepoint(pos):
                self._restart_game()
            return

        reset_button = self.action_buttons.get("reset_round")
        if reset_button and reset_button.collidepoint(pos):
            self.client.request_round_reset()
            return

        if snapshot["winner_id"] is not None:
            return

        if not snapshot["current_card"] or not snapshot["table_card"]:
            return

        valid_symbols = set(snapshot["current_card"]).intersection(snapshot["table_card"])
        for rect, symbol_id in self.click_targets:
            if rect.collidepoint(pos):
                if symbol_id in valid_symbols:
                    self.client.send_move(symbol_id)
                return

    def _draw(self, snapshot):
        self.action_buttons = {}
        self.screen.fill(BG)
        self._draw_header(snapshot)

        if snapshot["winner_id"] is not None:
            self._draw_game_end(snapshot)
        elif snapshot["error_message"] and not snapshot["is_connected"]:
            self._draw_error(snapshot)
        elif not snapshot["current_card"] or not snapshot["table_card"]:
            self._draw_lobby(snapshot)
        else:
            self._draw_game(snapshot)

    def _draw_header(self, snapshot):
        pygame.draw.rect(self.screen, PANEL, pygame.Rect(0, 0, WIDTH, HEADER_HEIGHT))
        pygame.draw.line(self.screen, LINE, (0, HEADER_HEIGHT), (WIDTH, HEADER_HEIGHT), 1)

        player = snapshot["my_id"]
        player_text = "Oczekiwanie na ID"
        if player is not None:
            player_text = f"Gracz {player + 1}"
        status = "polaczono" if snapshot["is_connected"] else "rozlaczono"
        if snapshot["winner_id"] is not None:
            status = "koniec gry"
        phase = "Gra"
        if snapshot["winner_id"] is not None:
            phase = "Koniec"
        elif snapshot["error_message"] and not snapshot["is_connected"]:
            phase = "Blad"
        elif not snapshot["current_card"] or not snapshot["table_card"]:
            phase = "Lobby"

        self._text("Double", self.fonts["title"], INK, (34, 18))
        self._text(
            "Rozgrywka online",
            self.fonts["small"],
            MUTED,
            (38, 62),
        )

        self._metric("Etap", phase, 350, 22, 156)
        self._metric("Gracz", player_text, 522, 22, 144)

        lobby = "..."
        if snapshot["max_players"] > 0:
            lobby = f"{snapshot['current_players']}/{snapshot['max_players']}"
        self._metric("Lobby", lobby, 682, 22, 126)

        card_text = "-"
        if snapshot["my_cards_count"]:
            card_number = min(
                snapshot["current_card_index"] + 1,
                snapshot["my_cards_count"],
            )
            card_text = f"{card_number}/{snapshot['my_cards_count']}"
        self._metric("Karta", card_text, 824, 22, 112)

        color = GOOD if "Trafienie" in snapshot["last_feedback"] else ACCENT
        if not snapshot["is_connected"] and snapshot["winner_id"] is None:
            color = MUTED
        self._pill(status, WIDTH - 146, 41, color)

    def _draw_lobby(self, snapshot):
        current = snapshot["current_players"]
        maximum = snapshot["max_players"]
        if maximum <= 0:
            counter = "Laczenie z serwerem..."
        else:
            counter = f"Lobby: {current}/{maximum}"

        center = (WIDTH // 2, HEIGHT // 2 + 8)
        pygame.draw.circle(self.screen, PANEL, center, 142)
        pygame.draw.circle(self.screen, LINE, center, 142, 2)
        pygame.draw.arc(
            self.screen,
            ACCENT,
            pygame.Rect(center[0] - 96, center[1] - 96, 192, 192),
            -math.pi / 2,
            -math.pi / 2 + (time.time() * 1.8) % (math.pi * 2),
            8,
        )

        self._center_text(counter, self.fonts["h2"], INK, center[0], center[1] - 16)
        self._center_text(
            "Czekam na komplet graczy",
            self.fonts["body"],
            MUTED,
            center[0],
            center[1] + 24,
        )

    def _draw_game(self, snapshot):
        self.click_targets = []

        left_center = (315, 430)
        right_center = (785, 430)
        radius = 204

        self._draw_card(
            "Karta na stole",
            snapshot["table_card"],
            left_center,
            radius,
            interactive=False,
        )
        self._draw_card(
            "Twoja karta",
            snapshot["current_card"],
            right_center,
            radius,
            interactive=True,
        )
        self._draw_round_controls(snapshot)
        self._draw_feedback(snapshot)

    def _draw_round_controls(self, snapshot):
        if snapshot["current_players"] < snapshot["max_players"]:
            text = "Zakoncz runde"
        else:
            text = "Glosuj reset"

        button = pygame.Rect(WIDTH // 2 - 88, HEIGHT - 78, 176, 42)
        self.action_buttons["reset_round"] = button
        self._button(button, text, MUTED)

        if snapshot["reset_needed"]:
            votes = f"{snapshot['reset_votes']}/{snapshot['reset_needed']}"
            self._center_text(f"Reset: {votes}", self.fonts["small"], MUTED, WIDTH // 2, HEIGHT - 96)
        elif snapshot["current_players"] < snapshot["max_players"]:
            self._center_text(
                "Zostales sam - mozesz wrocic do lobby",
                self.fonts["small"],
                MUTED,
                WIDTH // 2,
                HEIGHT - 96,
            )

    def _draw_card(self, label, symbols, center, radius, interactive):
        title = self.fonts["h2"].render(label, True, INK)
        title_rect = title.get_rect(center=(center[0], center[1] - radius - 32))
        self.screen.blit(title, title_rect)

        shadow = pygame.Surface((radius * 2 + 18, radius * 2 + 18), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (40, 50, 65, 28), (radius + 9, radius + 11), radius)
        self.screen.blit(shadow, (center[0] - radius - 9, center[1] - radius - 9))

        pygame.draw.circle(self.screen, PANEL, center, radius)
        pygame.draw.circle(self.screen, ACCENT if interactive else LINE, center, radius, 4)

        positions = self._symbol_positions(center, radius)
        for index, symbol_id in enumerate(symbols[: len(positions)]):
            pos = positions[index]
            rect = self._draw_symbol(symbol_id, pos, index)
            if interactive:
                self.click_targets.append((rect, symbol_id))

    def _draw_symbol(self, symbol_id, center, index):
        base_sizes = [62, 58, 56, 60, 54, 58, 56, 60]
        size = base_sizes[index % len(base_sizes)]
        image = self.symbols.get(symbol_id)

        rect = pygame.Rect(0, 0, size + 12, size + 12)
        rect.center = center
        pygame.draw.rect(self.screen, (247, 249, 252), rect, border_radius=8)
        pygame.draw.rect(self.screen, LINE, rect, width=1, border_radius=8)

        if image is None:
            self._center_text(str(symbol_id), self.fonts["h2"], INK, center[0], center[1])
            return rect

        scaled = pygame.transform.smoothscale(image, (size, size))
        image_rect = scaled.get_rect(center=center)
        self.screen.blit(scaled, image_rect)
        return rect

    def _draw_feedback(self, snapshot):
        message = snapshot["last_feedback"]
        if not message or time.time() - snapshot["last_feedback_time"] > 1.8:
            return

        color = GOOD if "Trafienie" in message else BAD
        rect = pygame.Rect(WIDTH // 2 - 150, HEADER_HEIGHT + 18, 300, 44)
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        self._center_text(message, self.fonts["body"], (255, 255, 255), rect.centerx, rect.centery)

    def _draw_game_end(self, snapshot):
        winner = snapshot["winner_id"]
        if winner == snapshot["my_id"]:
            heading = "Wygrales!"
            sub = "Twoja talia skonczyla sie jako pierwsza."
            color = GOOD
        else:
            heading = f"Wygral gracz {winner + 1}"
            sub = "Gra zostala zakonczona przez serwer."
            color = ACCENT

        center = (WIDTH // 2, HEIGHT // 2)
        pygame.draw.circle(self.screen, PANEL, center, 172)
        pygame.draw.circle(self.screen, color, center, 172, 5)
        self._center_text(heading, self.fonts["title"], INK, center[0], center[1] - 34)
        self._center_text(sub, self.fonts["body"], MUTED, center[0], center[1] + 10)
        button = pygame.Rect(center[0] - 86, center[1] + 48, 172, 42)
        self.action_buttons["restart"] = button
        self._button(button, "Nowa gra", ACCENT)
        self._center_text("R tez uruchamia ponownie", self.fonts["small"], MUTED, center[0], center[1] + 112)

    def _draw_error(self, snapshot):
        center = (WIDTH // 2, HEIGHT // 2)
        self._center_text("Brak polaczenia", self.fonts["title"], BAD, center[0], center[1] - 40)
        self._center_text(snapshot["error_message"], self.fonts["body"], MUTED, center[0], center[1] + 6)
        button = pygame.Rect(center[0] - 86, center[1] + 42, 172, 42)
        self.action_buttons["restart"] = button
        self._button(button, "Polacz ponownie", ACCENT)
        self._center_text("ESC zamyka okno", self.fonts["small"], MUTED, center[0], center[1] + 106)

    def _symbol_positions(self, center, radius):
        cx, cy = center
        outer = radius * 0.66
        inner = radius * 0.26
        slots = [
            (0, -inner),
            (-outer * 0.54, -outer * 0.58),
            (outer * 0.54, -outer * 0.58),
            (-outer * 0.78, 0),
            (outer * 0.78, 0),
            (-outer * 0.72, outer * 0.56),
            (outer * 0.72, outer * 0.56),
            (0, outer * 1.10),
        ]
        return [(cx + dx, cy + dy) for dx, dy in slots]

    def _find_common_symbol(self, player_card, table_card):
        common = set(player_card).intersection(table_card)
        if not common:
            return None
        return next(iter(common))

    def _load_symbols(self):
        symbols_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "symbols")
        )
        loaded = {}

        for symbol_id in range(1, 58):
            path = os.path.join(symbols_dir, f"{symbol_id - 1}.png")
            if os.path.exists(path):
                loaded[symbol_id] = pygame.image.load(path).convert_alpha()

        return loaded

    def _pill(self, text, x, y, color):
        rect = pygame.Rect(x, y, 112, 34)
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        self._center_text(text, self.fonts["small"], (255, 255, 255), rect.centerx, rect.centery)

    def _button(self, rect, text, color):
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, width=1, border_radius=8)
        self._center_text(text, self.fonts["body"], (255, 255, 255), rect.centerx, rect.centery)

    def _metric(self, label, value, x, y, width):
        rect = pygame.Rect(x, y, width, 58)
        pygame.draw.rect(self.screen, (248, 250, 252), rect, border_radius=8)
        pygame.draw.rect(self.screen, LINE, rect, width=1, border_radius=8)
        self._text(label, self.fonts["small"], MUTED, (x + 12, y + 8))
        self._text(value, self.fonts["body"], INK, (x + 12, y + 29))

    def _text(self, text, font, color, pos):
        surface = font.render(text, True, color)
        self.screen.blit(surface, pos)

    def _center_text(self, text, font, color, x, y):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(x, y))
        self.screen.blit(surface, rect)

    def _can_restart(self, snapshot):
        return snapshot["winner_id"] is not None or (
            snapshot["error_message"] and not snapshot["is_connected"]
        )

    def _restart_game(self):
        if self.auto_reconnecting:
            return
        self.auto_reconnecting = True
        self.client.reconnect()
        self.auto_reconnecting = False

    def close(self):
        self.client.close()
        pygame.quit()
        sys.exit()
