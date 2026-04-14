# main.py
from Client import GameClient
from threading import Thread

def start_game():
    client = GameClient(host='127.0.0.1', port=8000)

    if client.connect():
        

        client.wait_for_lobby()
        thread = Thread(target = client.receive_data, args = ())
        thread.start()
        #  Główna pętla gry po wystartowaniu
        while client.is_connected:
            aktCards  = client.myCards
            print(f"Moje karty: {aktCards}")

if __name__ == "__main__":
    start_game()