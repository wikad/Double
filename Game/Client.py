import socket
import threading
import time


class GameClient:
    def __init__(self, host="127.0.0.1", port=8000):
        self.host = host
        self.port = port
        self.sock = self._create_socket()

        self.lock = threading.RLock()
        self._reset_state()

    def _create_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        return sock

    def _reset_state(self):
        self.my_id = None
        self.is_connected = False
        self.error_message = ""

        self.myCards = []
        self.tableCard = []
        self.obecna_karta = 0

        self.winner_id = None
        self.current_players = 0
        self.max_players = 0
        self.last_feedback = ""
        self.last_feedback_time = 0.0
        self.reset_votes = 0
        self.reset_needed = 0
        self.round_reset_pending = False
        self.round_reset_reason = ""

    def connect(self):
        with self.lock:
            self._reset_state()
            self.sock = self._create_socket()

        try:
            self.sock.connect((self.host, self.port))
            with self.lock:
                self.is_connected = True
            return True
        except OSError as exc:
            with self.lock:
                self.error_message = f"Nie mozna polaczyc z serwerem: {exc}"
            return False

    def reconnect(self, retries=10, delay=0.25):
        self.close()

        for attempt in range(retries):
            if self.connect():
                self.start_receiver()
                return True

            if attempt < retries - 1:
                time.sleep(delay)

        return False

    def start_receiver(self):
        thread = threading.Thread(target=self.receive_data, daemon=True)
        thread.start()
        return thread

    def receive_data(self):
        pending = ""
        sock = self.sock

        while self.is_connected:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    with self.lock:
                        if self.sock is sock:
                            self._disconnect("Serwer zamknal polaczenie.")
                    return

                pending += chunk.decode("utf-8", errors="replace")
                pending = self._normalize_stream(pending)
                while "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    self._handle_message(line.strip())
                if pending.startswith("GAME_END:"):
                    self._handle_message(pending.strip())
                    pending = ""
            except socket.timeout:
                continue
            except OSError as exc:
                with self.lock:
                    if self.sock is sock:
                        self._disconnect(f"Utracono polaczenie: {exc}")
                return

    def _handle_message(self, message):
        if not message:
            return

        if message.startswith("WELCOME:"):
            with self.lock:
                self.my_id = self._safe_int(message.split(":", 1)[1])
            return

        if message.startswith("LOBBY_UPDATE:"):
            players = message.rsplit(" ", 1)[-1]
            if "/" in players:
                current, maximum = players.split("/", 1)
                with self.lock:
                    self.current_players = self._safe_int(current)
                    self.max_players = self._safe_int(maximum)
            return

        if message.startswith("YOUR_CARDS:"):
            with self.lock:
                self.myCards = self._parse_cards(message.split(":", 1)[1])
                self.obecna_karta = 0
            return

        if message.startswith("CARD_ON_TABLE:"):
            with self.lock:
                self.tableCard = self._parse_card(message.split(":", 1)[1])
            return

        if message.startswith("HIT:"):
            with self.lock:
                self.obecna_karta = min(self.obecna_karta + 1, len(self.myCards))
                self.last_feedback = "Trafienie!"
                self.last_feedback_time = time.time()
            return

        if message.startswith("NOT_ON_TABLE:"):
            with self.lock:
                self.last_feedback = "Ten symbol nie pasuje."
                self.last_feedback_time = time.time()
            return

        if message.startswith("GAME_END:"):
            with self.lock:
                self.winner_id = self._safe_int(message.split(":", 1)[1])
                self.last_feedback = "Koniec gry."
                self.last_feedback_time = time.time()
                self.is_connected = False
            return

        if message.startswith("RESET_STATUS:"):
            votes = message.split(":", 1)[1].strip()
            if "/" in votes:
                current, needed = votes.split("/", 1)
                with self.lock:
                    self.reset_votes = self._safe_int(current)
                    self.reset_needed = self._safe_int(needed)
                    self.last_feedback = f"Reset: {self.reset_votes}/{self.reset_needed}"
                    self.last_feedback_time = time.time()
            return

        if message.startswith("ROUND_RESET:"):
            with self.lock:
                self.round_reset_pending = True
                self.round_reset_reason = message.split(":", 1)[1].strip()
                self.last_feedback = "Runda zakonczona."
                self.last_feedback_time = time.time()
                self.is_connected = False
            return

        if message.startswith("ERROR:"):
            self._disconnect(message.split(":", 1)[1].strip())

    def send_move(self, symbol_id):
        with self.lock:
            connected = self.is_connected

        if not connected:
            return

        try:
            self.sock.sendall(f"PLAY:{symbol_id}\n".encode("utf-8"))
        except OSError as exc:
            self._disconnect(f"Nie udalo sie wyslac ruchu: {exc}")

    def request_round_reset(self):
        with self.lock:
            connected = self.is_connected

        if not connected:
            return

        try:
            self.sock.sendall(b"RESET_GAME\n")
            with self.lock:
                self.last_feedback = "Glos za resetem wyslany."
                self.last_feedback_time = time.time()
        except OSError as exc:
            self._disconnect(f"Nie udalo sie wyslac resetu: {exc}")

    def snapshot(self):
        with self.lock:
            current_card = []
            if 0 <= self.obecna_karta < len(self.myCards):
                current_card = list(self.myCards[self.obecna_karta])

            return {
                "my_id": self.my_id,
                "is_connected": self.is_connected,
                "error_message": self.error_message,
                "my_cards_count": len(self.myCards),
                "current_card_index": self.obecna_karta,
                "current_card": current_card,
                "table_card": list(self.tableCard),
                "winner_id": self.winner_id,
                "current_players": self.current_players,
                "max_players": self.max_players,
                "last_feedback": self.last_feedback,
                "last_feedback_time": self.last_feedback_time,
                "reset_votes": self.reset_votes,
                "reset_needed": self.reset_needed,
                "round_reset_pending": self.round_reset_pending,
                "round_reset_reason": self.round_reset_reason,
            }

    def close(self):
        with self.lock:
            self.is_connected = False
            sock = self.sock

        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()

    def _disconnect(self, message):
        with self.lock:
            self.error_message = message
            self.is_connected = False

    @staticmethod
    def _parse_cards(raw_data):
        cards = []
        for card_text in raw_data.strip().split("|"):
            card = GameClient._parse_card(card_text)
            if card:
                cards.append(card)
        return cards

    @staticmethod
    def _parse_card(raw_data):
        return [
            int(part.strip())
            for part in raw_data.split(",")
            if part.strip().isdigit()
        ]

    @staticmethod
    def _safe_int(value, default=0):
        try:
            text = str(value).strip()
            digits = ""
            for char in text:
                if char.isdigit():
                    digits += char
                else:
                    break
            return int(digits or text)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_stream(data):
        for marker in ("CARD_ON_TABLE:", "LOBBY_UPDATE:", "YOUR_CARDS:", "ERROR:", "RESET_STATUS:", "ROUND_RESET:"):
            data = data.replace(f"HIT:{marker}", f"HIT:\n{marker}")
        return data
