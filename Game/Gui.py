"""Interfejs Pygame: dwie okrągłe karty, kliknięcie wspólnego symbolu wysyła ruch."""
import colorsys
import math

import pygame

WIDTH, HEIGHT = 960, 600
CARD_RADIUS = 200
SYMBOL_RADIUS = 38
BG = (28, 32, 44)
CARD_FILL = (246, 244, 238)
TEXT = (235, 235, 240)
MUTED = (150, 156, 170)
GREEN = (80, 200, 120)
RED = (230, 90, 90)


def symbol_color(symbol):
    """Stały, łatwo rozróżnialny kolor dla każdego z 57 symboli."""
    hue = (symbol * 0.61803398875) % 1.0          # złoty podział - kolory równo rozłożone
    light = 0.45 if symbol % 2 else 0.58
    r, g, b = colorsys.hls_to_rgb(hue, light, 0.75)
    return int(r * 255), int(g * 255), int(b * 255)


def symbol_positions(center, count):
    """1 symbol w środku, reszta na okręgu."""
    cx, cy = center
    positions = [(cx, cy)]
    ring = count - 1
    for i in range(ring):
        angle = 2 * math.pi * i / ring - math.pi / 2
        positions.append((cx + 0.62 * CARD_RADIUS * math.cos(angle),
                          cy + 0.62 * CARD_RADIUS * math.sin(angle)))
    return positions


class GUI:
    def __init__(self, client):
        pygame.init()
        self.client = client
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Dobble")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 26, bold=True)
        self.small = pygame.font.SysFont("Arial", 20)
        self.symbol_font = pygame.font.SysFont("Arial", 28, bold=True)
        self.table_center = (WIDTH * 0.27, HEIGHT * 0.57)
        self.hand_center = (WIDTH * 0.73, HEIGHT * 0.57)
        self.hovered = None
        self.flash_until = 0

    # --- pętla ------------------------------------------------------------

    def run(self):
        running = True
        seen_seq = 0
        while running and self.client.is_connected:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._on_click(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self.hovered = self._symbol_at(event.pos)

            # Nowa odpowiedź serwera -> krótkie podświetlenie ramki karty
            if self.client.result_seq != seen_seq:
                seen_seq = self.client.result_seq
                self.flash_until = pygame.time.get_ticks() + 400

            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
        self.client.close()
        pygame.quit()

    def _on_click(self, pos):
        symbol = self._symbol_at(pos)
        if symbol is not None and self.client.winner_id is None:
            self.client.send_move(symbol)

    def _symbol_at(self, pos):
        card = self.client.my_current_card()
        for symbol, (x, y) in zip(card, symbol_positions(self.hand_center, len(card))):
            if math.hypot(pos[0] - x, pos[1] - y) <= SYMBOL_RADIUS:
                return symbol
        return None

    # --- rysowanie --------------------------------------------------------

    def draw(self):
        self.screen.fill(BG)
        c = self.client
        if c.error:
            self._center_text(c.error, RED)
        elif not c.my_cards or not c.table_card:
            self._center_text(f"Czekam na graczy... {c.current_players}/{c.max_players or '?'}", TEXT)
        else:
            self._draw_game()
            if c.winner_id is not None:
                self._draw_end()

    def _draw_game(self):
        c = self.client
        header = self.font.render(f"Gracz {c.my_id}", True, TEXT)
        self.screen.blit(header, (32, 24))
        info = self.small.render(
            f"Zostało kart: {c.cards_left}/{len(c.my_cards)}   ·   kliknij symbol, który jest na obu kartach",
            True, MUTED)
        self.screen.blit(info, (32, 62))

        self._draw_card(c.table_card, self.table_center, "Stół")
        border = None
        if pygame.time.get_ticks() < self.flash_until:
            border = GREEN if c.last_result == "hit" else RED if c.last_result == "miss" else None
        self._draw_card(c.my_current_card(), self.hand_center, "Twoja karta", border, interactive=True)

    def _draw_card(self, symbols, center, label, border=None, interactive=False):
        cx, cy = int(center[0]), int(center[1])
        pygame.draw.circle(self.screen, (16, 18, 26), (cx + 6, cy + 8), CARD_RADIUS)  # cień
        pygame.draw.circle(self.screen, CARD_FILL, (cx, cy), CARD_RADIUS)
        if border:
            pygame.draw.circle(self.screen, border, (cx, cy), CARD_RADIUS, 8)
        text = self.small.render(label, True, MUTED)
        self.screen.blit(text, (cx - text.get_width() // 2, cy - CARD_RADIUS - 30))

        for symbol, (x, y) in zip(symbols, symbol_positions(center, len(symbols))):
            r = SYMBOL_RADIUS + (4 if interactive and symbol == self.hovered else 0)
            pygame.draw.circle(self.screen, symbol_color(symbol), (int(x), int(y)), r)
            num = self.symbol_font.render(str(symbol), True, (255, 255, 255))
            self.screen.blit(num, (int(x) - num.get_width() // 2, int(y) - num.get_height() // 2))

    def _draw_end(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        won = self.client.winner_id == self.client.my_id
        msg = "Wygrałeś!" if won else f"Wygrywa gracz {self.client.winner_id}"
        self._center_text(msg, GREEN if won else TEXT)

    def _center_text(self, msg, color):
        text = self.font.render(msg, True, color)
        self.screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - text.get_height() // 2))
