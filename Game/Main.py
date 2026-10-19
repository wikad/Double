"""Uruchomienie klienta: python Main.py  (adres serwera: DOBBLE_HOST, domyślnie 127.0.0.1)"""
import sys

from Client import GameClient
from Gui import GUI


def main():
    client = GameClient()
    if not client.connect():
        print(client.error)
        sys.exit(1)
    GUI(client).run()


if __name__ == "__main__":
    main()
