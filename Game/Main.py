# main.py
from Client import GameClient
from threading import Thread
import time
from Gui import GUI
def start_game():
    client = GameClient(host='127.0.0.1', port=8000)
    game = GUI(client)
    if client.connect():
        
        thread = Thread(target = client.receive_data, args = ())
        thread.start()
        print("halo")

        print("Połączono. Oczekiwanie na inicjalizację danych...")

        # 3. CZEKAMY na Handshake (aż wpadnie my_id)
        while client.is_connected and client.my_id is None:
            time.sleep(0.1)
        print(f"Zalogowano! Moje ID: {client.my_id}")

        #  Główna pętla gry po wystartowaniu
        while client.is_connected:
            
            game.lobby()
            # if(client.current_players != client.max_players and client.max_players > 0):
            #      print(f"graczy{client.current_players} / {client.max_players}")

            # else:
                # Sprawdź czy karty NIE są None ORAZ czy lista nie jest pusta
            if client.myCards and client.tableCard:
                game.gameLoop()
            #         print("\n--- STATUS GRY ---")
            #         print(f"Karta na stole: {client.tableCard}")
            #         print(f"Twoja karta:    {client.myCards[client.obecna_karta]}")
                    
            #         # Prosta obsługa błędnego indeksu na wszelki wypadek
            #         try:
            #             wybor = input("Podaj symbol (lub 'q' aby wyjść): ")
            #         except EOFError:
            #             break

            #         if wybor == 'q':
            #             client.close()
            #             return
                    
            #         client.send_move(wybor)
            #         # Po wysłaniu ruchu dajemy ułamek sekundy na odświeżenie danych z serwera
            #         time.sleep(0.1)
            # else:
            #         # Jeśli wejdzie w else, ale kart jeszcze nie ma, wypisz komunikat raz
            #         print("Czekam na rozdanie kart...", end="\r")
            #         time.sleep(0.5)
            # pass

if __name__ == "__main__":
    start_game()