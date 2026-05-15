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
        self.winner_id = None
        self.obecna_karta = 0
        self.current_players =0
        self.max_players =0
    def connect(self):
        """Inicjalizuje socket i łączy z serwerem."""
        try:
            self.sock.connect((self.host, self.port))
            self.is_connected = True
            
            return True
        except Exception as e:
            print(f"Błąd połączenia: {e}")
            return False

    # wyciaganie kart z wiadomosci 
    def extract_cards_from_message(self, message):
        if "YOUR_CARDS:" in message:
            try:
                raw_data = message.replace("YOUR_CARDS:", "").strip()
                card_strings = list(filter(None, raw_data.split('|')))
                new_cards = []
                for card_str in card_strings:
                    if card_str.strip():
                        symbols = [int(s.strip()) for s in card_str.split(',') if s.strip()]
                        new_cards.append(symbols)
                self.myCards = new_cards
                print(f"Pomyślnie sparsowano {len(self.myCards)} kart.")
            except Exception as e:
                print(f"Nie udało się sparsować kart. Błąd: {e}")

    #odbiera data od serwera 
    def receive_data(self):

        """Odbiera dane wrzuca je do karta na stole."""
        while(1):
            if not self.is_connected:
                return
            try:# coś takiego to by wyglądało żeby przypisać odebrane karty do tablicy 
                data = self.sock.recv(2048).decode('utf-8')
                if (data):
                    if "WELCOME:" in data:
                        self.my_id = int(data.split(":")[-1].strip())
                        print(f"Otrzymałem ID gracza: {self.my_id}")
                    if "CARD_ON_TABLE:" in data:
                        try:
                            raw_card = data.split("CARD_ON_TABLE:")[-1].strip()
                            self.tableCard = [int(s.strip()) for s in raw_card.split(',') if s.strip()]
                            print(f"Zaktualizowano kartę na stole: {self.tableCard}")
                        except Exception as e:
                            print(f"Błąd parsowania karty na stole: {e}")
                        pass
                    if "GAME_END:" in data:
                        # przekazanie do gui że gra się zakończyła
                        self.winner_id = int(data.split(":")[-1].strip())
                        print(f"KONIEC GRY. Zwycięzca: {self.winner_id}")
                        print("Gra zakończona!")
                        self.is_connected = False
                    if "NOT_ON_TABLE:" in data:
                        # przekazanie do gui że nie udało sie trafic karty 
                        # wywołanie czegos z gui będzie trzeba przekazać obiek gui 
                        print("DUPA KURWO JEBANA")
                        pass
                    if "HIT:" in data:
                        #karta trafiona nowa karta jako obecna gracza z mycards
                        # wywołanie czegos z gui będzie trzeba przekazać obiek gui
                        self.obecna_karta += 1 
                        print("JASNY GWINT TRAFIŁEŚ GNOJU")
                        pass
                    if "YOUR_CARDS:" in data: # to jest wiadomość startowa z kartami gracza
                        self.extract_cards_from_message(data) # mam nadzieje że działa
                        print(f"Otrzymałem karty: {self.myCards}")
                    if "LOBBY_UPDATE:" in data:
                        ratio_part = data.split()[-1] 
                        current_str, max_str = ratio_part.split('/')
                        self.current_players = int(current_str)
                        self.max_players = int(max_str)
                        #przekazać to do gui narazie forma debugowania 
                        
                        pass
                    if "ERROR:" in data:
                        print("error")
                        return 
                        pass #brak miejsca w lobby
            except:
                self.is_connected = False
                return

    def send_move(self, move_str):
        message = f"PLAY:{move_str}\n" 
        self.sock.sendall(message.encode('utf-8'))
        print(f"Wysłano ruch: {message.strip()}")

    def close(self):
        self.sock.close()
        self.is_connected = False