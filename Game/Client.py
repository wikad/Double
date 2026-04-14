import socket
import threading

#SSZYMON NIE PATRZ NA EXCEPT TO SIE KOD PRSOTY I NIE SKĄPLIKOWANY ROBI 


class GameClient:
    def __init__(self, host='127.0.0.1', port=8000):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_id = None
        self.is_connected = False
        self.myCards = [] # Tu możesz przechowywać twoje karty
        self.tableCards = [] # Tu możesz przechowywać karty na stole

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

    def wait_for_lobby(self):
        """Pętla oczekiwania na start gry (Handshake 2)."""
        print("Oczekiwanie na graczy w lobby...")
        while self.is_connected:
            data = self.receive_data()
            print(f"Serwer: {data}")
            
            if "GAME_START" in data:
                print("Gra właśnie się rozpoczęła!")
                self.extract_cards_from_message(data)
                break

    def extract_cards_from_message(self, message):
        """Przykłądowa funkcja która wyciąga karty z data"""
        if "Twoje karty:" in message:
            try:
                cards_part = message.split(",")[-1].strip()

                print(f"Zapisano karty do tablicy: {cards_part}")
                self.myCards = cards_part # Przykładowe rozdzielenie kart do listy
            except:
                print("Nie udało się sparsować kart.")

    def receive_data(self):
        """Odbiera dane wrzuca je do karta na stole."""
        while(1):
            if not self.is_connected:
                return
            try:# coś takiego to by wyglądało żeby przypisać odebrane karty do tablicy 
                data = self.sock.recv(2048).decode('utf-8')
                if (data):
                    if "CARD_ON_TABLE:" in data:
                        self.tableCards = data.split(":")[1].strip() # Przykładowe rozdzielenie kart na stole
                        print(f"Aktualizacja kart na stole: {self.tableCards}")
                    if "GAME_END" in data:
                        print("Gra zakończona!")
                        self.is_connected = False
                    if "NOT_ON_TABLE" in data:
                        print("Nie masz tego symbolu na karcie na stole!")
                    
            except:
                self.is_connected = False
                return

    def send_move(self, move_str):
        """Wysyła ruch gracza do serwera."""
        if self.is_connected:
            try:
                self.sock.sendall(move_str.encode('utf-8'))
            except Exception as e:
                print(f"Błąd wysyłania: {e}")
                self.is_connected = False

    def close(self):
        self.sock.close()
        self.is_connected = False