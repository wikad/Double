# main.py
from Client import GameClient
from threading import Thread
import time
def start_game():
    client = GameClient(host='127.0.0.1', port=8000)

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
            print("halo")
            if(client.current_players != client.max_players and client.max_players > 0):
                 print(f"graczy{client.current_players} / {client.max_players}")
                 print("halo")
            else:
                print("halo")
                print(client.tableCard)
                print(client.myCards[client.obecna_karta])
                wybor = str(input("Podaj symbol: "))
                client.send_move(wybor)
            pass

if __name__ == "__main__":
    start_game()