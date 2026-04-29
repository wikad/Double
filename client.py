import socket
import threading
import time

HOST = "127.0.0.1"
PORT = 8000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

print("Połączono z serwerem")

# ----------- STAN GRY -----------

table_card = []
my_cards = []
current_card_index = 0

lock = threading.Lock()

# ----------- PARSOWANIE -----------

def parse_table(msg):
    global table_card
    with lock:
        data = msg.split(":")[1].strip()
        table_card = [int(x) for x in data.split(",") if x]

        print("🟡 Karta na stole:", table_card)


def parse_cards(msg):
    global my_cards
    with lock:
        data = msg.split(":")[1].strip()
        cards_raw = data.split("|")

        my_cards = []
        for card in cards_raw:
            if card:
                symbols = [int(x) for x in card.split(",") if x]
                my_cards.append(symbols)

        print(f"🟢 Mam {len(my_cards)} kart")


def handle_hit():
    global current_card_index
    with lock:
        current_card_index += 1
        print(f"✅ Trafione, następna karta: {current_card_index + 1}/{len(my_cards)}")


# ----------- AI -----------

def find_match():
    with lock:
        if not table_card or current_card_index >= len(my_cards):
            return None

        for symbol in my_cards[current_card_index]:
            if symbol in table_card:
                return symbol
    return None


def play(symbol):
    msg = f"PLAY:{symbol}\n"
    sock.send(msg.encode())
    print(f"🚀 Gram: {symbol}")


# ----------- ODBIERANIE -----------

def receiver():
    buffer = ""

    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break

            buffer += data.decode()

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                print("📩", line)

                if line.startswith("CARD_ON_TABLE:"):
                    parse_table(line)

                elif line.startswith("YOUR_CARDS:"):
                    parse_cards(line)

                elif line == "HIT":
                    handle_hit()

        except Exception as e:
            print("Błąd:", e)
            break
# ----------- MAIN LOOP -----------

threading.Thread(target=receiver, daemon=True).start()

while True:
    time.sleep(0.5)

    symbol = find_match()
    if symbol is not None:
        play(symbol)
        time.sleep(0.3)  # żeby nie spamować za szybko
