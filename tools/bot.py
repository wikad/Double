"""
Bot do testowania serwera: łączy się, czeka na karty i gra sam,
szukając wspólnego symbolu z opóźnieniem (żeby człowiek miał szansę).

    python tools/bot.py            # domyślnie 1.5 s na ruch
    python tools/bot.py --delay 0.5
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Game"))
from Client import GameClient  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=1.5, help="czas namysłu bota w sekundach")
    args = parser.parse_args()

    client = GameClient()
    if not client.connect():
        sys.exit(client.error)
    print("Bot połączony, czekam na rozdanie...")

    while client.is_connected and client.winner_id is None:
        time.sleep(args.delay)
        card, table = client.my_current_card(), client.table_card
        common = set(card) & set(table)
        if common:
            symbol = common.pop()
            client.send_move(symbol)
            print(f"Bot {client.my_id}: gram symbol {symbol} (zostało {client.cards_left - 1})")

    if client.winner_id is not None:
        print(f"Koniec gry, wygrał gracz {client.winner_id}")
    client.close()


if __name__ == "__main__":
    main()
