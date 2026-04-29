import socket
import threading


class GameClient:
    def __init__(self, host='127.0.0.1', port=8000):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_id = None
        self.is_connected = False
        self.myCards = [] # Tu możesz przechowywać twoje karty
        self.tableCard = [] # Tu możesz przechowywać karty na stole

    def connect(self):
        """Inicjalizuje socket i łączy z serwerem."""
        try:
            self.sock.connect((self.host, self.port))
            self.is_connected = True
            
            # Odbierz pierwszy komunikat: WELCOME (Handshake 1)
            data = self.receive_data()
            if "WELCOME" in data:
                self.my_id = int(data.split()[-1])
                print(f"Połączono! Moje ID to: {self.my_id}")
            return True
        except Exception as e:
            print(f"Błąd połączenia: {e}")
            return False

    # wyciaganie kart z wiadomosci 
    def extract_cards_from_message(self, message):
        """Przykłądowa funkcja która wyciąga karty z data"""
        if "YOUR_CARDS:" in message:
            try:
                pass # zrobic pasrowanie kart z wiadomośći do myCards
            except:
                print("Nie udało się sparsować kart.")

    #odbiera data od serwera 
    def receive_data(self):

        """Odbiera dane wrzuca je do karta na stole."""
        while(1):
            if not self.is_connected:
                return
            try:# coś takiego to by wyglądało żeby przypisać odebrane karty do tablicy 
                data = self.sock.recv(2048).decode('utf-8')
                if (data):
                    if "CARD_ON_TABLE:" in data:
                        print(f"karta na stole {data}")
                    if "GAME_END" in data:
                        print("Gra zakończona!")
                        self.is_connected = False
                    if "NOT_ON_TABLE" in data:
                        print("Nie masz tego symbolu na karcie na stole!")
                    if "HIT" in data:
                        print("karta trafiona")
                    if "YOUR_CARDS:" in data: # to jest wiadomość startowa 
                        self.extract_cards_from_message(data)
                    if "LOBBY_UPDATE:" in data:
                        print(f"oczekiwanie na graczy {data}")
            except:
                self.is_connected = False
                return

    def send_move(self, move_str):
        """Wysyła ruch gracza do serwera."""

        # to musi być waidomość PLAY: 6 na przykład to nie jest zroibone 
        if self.is_connected:
            try:
                self.sock.sendall(move_str.encode('utf-8'))
            except Exception as e:
                print(f"Błąd wysyłania: {e}")
                self.is_connected = False

    def close(self):
        self.sock.close()
        self.is_connected = False