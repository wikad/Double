"""Klient sieciowy gry Dobble: protokół tekstowy, jedna wiadomość = jedna linia."""
import os
import socket
import threading


class GameClient:
    def __init__(self, host=None, port=None):
        self.host = host or os.getenv("DOBBLE_HOST", "127.0.0.1")
        self.port = int(port or os.getenv("DOBBLE_PORT", 8000))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = threading.Lock()

        self.is_connected = False
        self.my_id = None
        self.my_cards = []        # lista kart, karta = lista symboli
        self.table_card = []      # karta na środku stołu
        self.current_card = 0     # indeks mojej bieżącej karty
        self.current_players = 0
        self.max_players = 0
        self.winner_id = None
        self.last_result = None   # "hit" / "miss" - do podświetlenia w GUI
        self.result_seq = 0       # licznik odpowiedzi serwera na ruchy
        self.error = None

    # --- połączenie -------------------------------------------------------

    def connect(self):
        try:
            self.sock.connect((self.host, self.port))
        except OSError as e:
            self.error = f"Nie można połączyć z {self.host}:{self.port} ({e})"
            return False
        self.is_connected = True
        threading.Thread(target=self._receive_loop, daemon=True).start()
        return True

    def close(self):
        self.is_connected = False
        try:
            self.sock.close()
        except OSError:
            pass

    def send_move(self, symbol):
        try:
            self.sock.sendall(f"PLAY:{symbol}\n".encode("utf-8"))
        except OSError:
            self.is_connected = False

    # --- odbieranie -------------------------------------------------------

    def _receive_loop(self):
        """TCP to strumień: składamy dane w bufor i przetwarzamy pełne linie."""
        buffer = ""
        while self.is_connected:
            try:
                data = self.sock.recv(2048)
            except OSError:
                break
            if not data:
                break
            buffer += data.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    self._handle_message(line.strip())
        self.is_connected = False

    def _handle_message(self, line):
        command, _, payload = line.partition(":")
        with self.lock:
            if command == "WELCOME":
                self.my_id = int(payload)
            elif command == "LOBBY_UPDATE":
                current, maximum = payload.split()[-1].split("/")
                self.current_players, self.max_players = int(current), int(maximum)
            elif command == "YOUR_CARDS":
                self.my_cards = [
                    [int(s) for s in card.split(",") if s]
                    for card in payload.split("|") if card
                ]
                self.current_card = 0
            elif command == "CARD_ON_TABLE":
                self.table_card = [int(s) for s in payload.split(",") if s]
            elif command == "HIT":
                self.current_card += 1
                self.last_result = "hit"
                self.result_seq += 1
            elif command == "NOT_ON_TABLE":
                self.last_result = "miss"
                self.result_seq += 1
            elif command == "GAME_END":
                self.winner_id = int(payload)
            elif command == "ERROR":
                self.error = payload.strip()

    # --- stan dla GUI -----------------------------------------------------

    def my_current_card(self):
        with self.lock:
            if self.current_card < len(self.my_cards):
                return list(self.my_cards[self.current_card])
            return []

    @property
    def cards_left(self):
        return max(0, len(self.my_cards) - self.current_card)
