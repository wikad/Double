import argparse

from Client import GameClient
from Gui import GUI
host="127.0.0.1"

def start_game(host="127.0.0.1", port=8000):
    client = GameClient(host=host, port=port)
    if client.connect():
        client.start_receiver()

    game = GUI(client)
    game.run()


def parse_args():
    parser = argparse.ArgumentParser(description="Klient gry Double")
    parser.add_argument("--host", default="127.0.0.1", help="Adres serwera")
    parser.add_argument("--port", default=8000, type=int, help="Port serwera")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    start_game(args.host, args.port)
