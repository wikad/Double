#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <pthread.h>
#include <time.h>

// Autorzy: Wiktor Adamczyk, Maciej Drywa, Szymon Drywa, Paweł Krajewski
// GRA DOUBLE
// Projekt przedstawia sieciową wersję gry Double/Dobble dla paru graczy.
// Serwer odpowiada za przyjmowanie klientów, przydzielanie im identyfikatorów,
// generowanie i tasowanie kart, sprawdzanie poprawności ruchów oraz rozsyłanie
// informacji o stanie gry. Każdy klient jest obsługiwany w osobnym wątku, a
// wspólny stan gry jest chroniony mutexem.




#define MAX_CLIENTS 3 //liczba graczy
#define PORT 8000 //Port na którym nasłuchuje serwer
#define CARDS_PER_PLAYER 10 //ilość kart dla gracza

// Serwer tworzy 57 kart i 8 kart na każdej karcie
#define N 7
#define MAX_SYMBOLS (N*N + N + 1)
#define CARDS (N*N + N + 1)
#define SYMBOLS_PER_CARD (N + 1)


// Stan Gry
int player_cards[MAX_CLIENTS][CARDS_PER_PLAYER][SYMBOLS_PER_CARD]; //id gracza, numer karty, symbol na karcie
int table_card[SYMBOLS_PER_CARD]; // karta w centrum stolu
int cards[CARDS][SYMBOLS_PER_CARD]; //talia kart
int deck_order[CARDS];
int game_started = 0;
int game_over = 0;
int game_number = 0;
int reset_votes[MAX_CLIENTS];
// Struktura gracza
typedef struct {
    int socket;
    int id;
    int is_ready;
    int used_cards; //ilość zagranych kart
} player_t;

//aktywni gracze
player_t *clients[MAX_CLIENTS];
int client_count = 0;
pthread_mutex_t clients_mutex = PTHREAD_MUTEX_INITIALIZER; //każdy klient w osobnym wątku

//bezpieczne zakończenie : brak wysyłania SIGPIPE gdy klient się rozłączy
ssize_t send_to_client(int socket, const void *buffer, size_t length) {
    return send(socket, buffer, length, MSG_NOSIGNAL);
}

// funckje do tasowania symboli na karcie
void shuffle_int_array(int *array, int size) {
    for (int i = size - 1; i > 0; i--) {
        int j = rand() % (i + 1);
        int tmp = array[i];
        array[i] = array[j];
        array[j] = tmp;
    }
}

void shuffle_deck_order() {
    for (int i = 0; i < CARDS; i++) {
        deck_order[i] = i;
    }

    shuffle_int_array(deck_order, CARDS);
}

//resetowanie stanu gry
void reset_game_state() {
    game_started = 0;
    game_over = 0;
    memset(player_cards, 0, sizeof(player_cards));
    memset(table_card, 0, sizeof(table_card));
    memset(deck_order, 0, sizeof(deck_order));
    memset(reset_votes, 0, sizeof(reset_votes));
}

//zlicza ile graczy zagłosowało za resetem
int count_reset_votes() {
    int votes = 0;
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i] != NULL && reset_votes[i]) {
            votes++;
        }
    }
    return votes;
}

//wysłanie komunikatu do klientów o resecie
void broadcast_reset_status_locked() {
    char buffer[64];
    sprintf(buffer, "RESET_STATUS:%d/%d\n", count_reset_votes(), client_count);

    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i] != NULL) {
            send_to_client(clients[i]->socket, buffer, strlen(buffer));
        }
    }
}
//Koniec rozgrywki po zagłosowaniu za resetem
void finish_round_locked(const char *reason) {
    char buffer[96];
    sprintf(buffer, "ROUND_RESET:%s\n", reason);
    game_over = 1;

    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i] != NULL) {
            send_to_client(clients[i]->socket, buffer, strlen(buffer));
            shutdown(clients[i]->socket, SHUT_RDWR);
        }
    }
}

//generacja decku
void generate_dobble() {

    int i, j, k;

    int card_index = 0;

    for (i = 0; i < N + 1; i++) {

        cards[card_index][0] = 1;

        for (j = 0; j < N; j++) {
            cards[card_index][j + 1] = (j + 1) + (i * N) + 1;
        }

        card_index++;
    }

    for (i = 0; i < N; i++) {
        for (j = 0; j < N; j++) {

            cards[card_index][0] = i + 2;

            for (k = 0; k < N; k++) {

                int val = (N + 1 + N * k + (i * k + j) % N) + 1;

                cards[card_index][k + 1] = val;
            }

            card_index++;
        }
    }
}

//przypisanie kart dla gracza  karta nr 0 przeznaczona jako karta na stół 
void generate_deck_for_player(int player_id) { 
    
    int start = 1 + player_id * CARDS_PER_PLAYER;

    for (int i = 0; i < CARDS_PER_PLAYER; i++) {
        int card_index = deck_order[start + i];

        for (int j = 0; j < SYMBOLS_PER_CARD; j++) {

            player_cards[player_id][i][j] = cards[card_index][j];
        }
        //tasowanie symboli na karcie
        shuffle_int_array(player_cards[player_id][i], SYMBOLS_PER_CARD);
    }
}

// Funkcja do wysyłania wiadomości do wszystkich o oczekiwaniu w lobby taki starterek
void broadcast_lobby_status() {
    char buffer[128];
    pthread_mutex_lock(&clients_mutex);
    
    sprintf(buffer, "LOBBY_UPDATE: Graczy w lobby: %d/%d\n", client_count, MAX_CLIENTS);
    
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i] != NULL) {
            send_to_client(clients[i]->socket, buffer, strlen(buffer));
        }
    }
    pthread_mutex_unlock(&clients_mutex);
}
// wysyła karte gracza kurwa jednak wysyła wszystkie karty gracza jakie ma 
void send_player_cards(player_t *p) { //format wysylanej wiadomosci 1,2,3,4,5,|3,5,2,1,3| 
    char buffer[512] = "YOUR_CARDS:";

    for (int i = 0; i < CARDS_PER_PLAYER; i++) {
        for (int j = 0; j < SYMBOLS_PER_CARD; j++) {
            char tmp[16];
            sprintf(tmp, "%d,", player_cards[p->id][i][j]);
            strcat(buffer, tmp);
        }
        strcat(buffer, "|");
    }
    strcat(buffer, "\n");

    send_to_client(p->socket, buffer, strlen(buffer));
}

// wybiera karte na stół
void generate_table_card()
{
    int card_index = deck_order[0];
    for (int i = 0; i < SYMBOLS_PER_CARD; i++) {
        table_card[i] = cards[card_index][i];
    }
    //tasowanie symboli na karcie
    shuffle_int_array(table_card, SYMBOLS_PER_CARD);
}

// Funkcja do wysyłania informacji o nowej karcie na stole do wszystkich klientów za każdym razem gdy trafiona karta jest przez klienta 
void broadcast_card_on_table(int *new_card) {
    char buffer[256]; 
    char temp[16];
    
    pthread_mutex_lock(&clients_mutex);
    
    // Początek wiadomości
    strcpy(buffer, "CARD_ON_TABLE:");

    // Doklejanie symboli z tablicy
    for (int i = 0; i < SYMBOLS_PER_CARD; i++) {
        if (i < SYMBOLS_PER_CARD - 1) {
            sprintf(temp, "%d,", new_card[i]);
        } else {
            sprintf(temp, "%d", new_card[i]);
        }
        strcat(buffer, temp);
    }
    
    strcat(buffer, "\n"); // Koniec linii dla klienta

    // Wysłanie do wszystkich
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i] != NULL) {
            send_to_client(clients[i]->socket, buffer, strlen(buffer));
        }
    }
    
    pthread_mutex_unlock(&clients_mutex);
}
// czy katra graczy = karta na stole
int symbol_matches_table(int symbol)
{
    for(int i=0; i<SYMBOLS_PER_CARD; i++)
    {
        if(table_card[i]==symbol)
            return 1;
    }
    return 0;
}

int symbol_matches_player_card(player_t *p, int symbol)
{
    if (p->used_cards >= CARDS_PER_PLAYER) {
        return 0;
    }

    for (int i = 0; i < SYMBOLS_PER_CARD; i++) {
        if (player_cards[p->id][p->used_cards][i] == symbol) {
            return 1;
        }
    }

    return 0;
}

void *connection_handler(void *arg) {
    player_t *p = (player_t *)arg;
    char buffer[2048];
    int read_size;

    // --- HANDSHAKE 1: Nadanie ID ---
    sprintf(buffer, "WELCOME:%d\n", p->id);
    send_to_client(p->socket, buffer, strlen(buffer));
   
   //oczekiwanie na maks graczy
    while(1) {
        pthread_mutex_lock(&clients_mutex);
        if (client_count >= MAX_CLIENTS) { 
            pthread_mutex_unlock(&clients_mutex);
            break; 
        }
        pthread_mutex_unlock(&clients_mutex);
        usleep(100000); // Śpij 0.1s, żeby nie męczyć procesora
    }


    // wysyłanie pierwszej karty 
    generate_deck_for_player(p->id); // generacja każdemu deck  
    for(int i=0; i<CARDS_PER_PLAYER; i++)
    {
        printf("Gracz %d karta %d: ", p->id, i);
        for(int j=0; j<SYMBOLS_PER_CARD; j++)
        {
            printf("%d ", player_cards[p->id][i][j]);
        }
        printf("\n");
    }
    send_player_cards(p);

    // --- GŁÓWNA PĘTLA GRY ---
    while ((read_size = recv(p->socket, buffer, sizeof(buffer) - 1, 0)) > 0) {
        buffer[read_size] = '\0';

        char *saveptr;
        char *message = strtok_r(buffer, "\n", &saveptr);
        while (message != NULL) {
            int should_stop = 0;

            // sprawdza info od gracza gracz odsyła tylko ifo o symbolu na karcie server trackuje na której jest
            if (strncmp(message, "PLAY:", 5) == 0) {
                int symbol = atoi(message + 5);
                int hit = 0;
                int game_ended = 0;
                int card_to_broadcast[SYMBOLS_PER_CARD];

                pthread_mutex_lock(&clients_mutex);
                //sprawdzenie warunku trafienia karty przez gracza
                if (symbol_matches_table(symbol) && symbol_matches_player_card(p, symbol)) {
                    for (int i=0; i<SYMBOLS_PER_CARD; i++) //kopiowanie karty gracza na stół
                    {
                        table_card[i]=player_cards[p->id][p->used_cards][i];
                        card_to_broadcast[i]=table_card[i];
                    }
                    p->used_cards++;
                    hit = 1;
                }
                pthread_mutex_unlock(&clients_mutex);

                if (hit) { //sprawdzenie czy gracz wygrał rozgrywkę
                    if (p->used_cards >= CARDS_PER_PLAYER) {
                        char win_msg[64];
                        sprintf(win_msg, "GAME_END:%d\n", p->id);

                        // Powiadom wszystkich o końcu gry
                        pthread_mutex_lock(&clients_mutex);
                        game_over = 1;
                        game_ended = 1;
                        for (int i = 0; i < MAX_CLIENTS; i++) {
                            if (clients[i] != NULL) {
                                send_to_client(clients[i]->socket, win_msg, strlen(win_msg));
                                shutdown(clients[i]->socket, SHUT_RDWR);
                            }
                        }
                        pthread_mutex_unlock(&clients_mutex);

                        
                    }
                    //wyślij nową kartę na stole do innych graczy
                    if (!game_ended) {
                        send_to_client(p->socket, "HIT:\n", 4);
                        broadcast_card_on_table(card_to_broadcast);
                    }
                }

                should_stop = game_ended;
                //możliwość resetu gry jeśli liczba głosów jest równa liczbie klientóœ
            } else if (strncmp(message, "RESET_GAME", 10) == 0) {
                pthread_mutex_lock(&clients_mutex);
                if (game_started && clients[p->id] != NULL) {
                    reset_votes[p->id] = 1;
                    broadcast_reset_status_locked();

                    if (client_count > 0 && count_reset_votes() >= client_count) {
                        finish_round_locked("vote");
                        should_stop = 1;
                    }
                }
                pthread_mutex_unlock(&clients_mutex);
            }

            if (should_stop) {
                break;
            }

            message = strtok_r(NULL, "\n", &saveptr);
        }

        usleep(40000);
        printf("Gracz %d wysłał ruch: %s", p->id, buffer);
        
        memset(buffer, 0, 2048);
    }

    // Rozłączenie
    printf("Gracz %d opuścił grę.\n", p->id);
    close(p->socket);
    
    //usuwanie gracza z tablicy clients i zmniejsza liczbę klientów
    pthread_mutex_lock(&clients_mutex);
    clients[p->id] = NULL;
    reset_votes[p->id] = 0;
    client_count--;
    //reset serwera kiedy nie ma już klientów w grze
    if (client_count <= 0) {
        client_count = 0;
        reset_game_state();
        printf("Serwer gotowy na nowa gre.\n");
    } else if (game_started && !game_over) {
        broadcast_reset_status_locked();
        if (count_reset_votes() >= client_count) {
            finish_round_locked("vote");
        }
    }
    pthread_mutex_unlock(&clients_mutex);
    
    broadcast_lobby_status();
    free(p);
    return NULL;
}

int main() {

    
    int listenfd, connfd;
    struct sockaddr_in serv_addr;
    pthread_t thread_id;

    listenfd = socket(AF_INET, SOCK_STREAM, 0); //Tworzenie socketu
    if (listenfd < 0) {
        perror("socket");
        return 1;
    }

    int opt = 1; //ustawienie flagi SO_REUSEADDR do łatwiejszego restartu
    if (setsockopt(listenfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        close(listenfd);
        return 1;
    }

    memset(&serv_addr, 0, sizeof(serv_addr));
    //wypełnianie strukltury adresu
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    serv_addr.sin_port = htons(PORT);

    //przypięcie socketu do portu
    if (bind(listenfd, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        perror("bind");
        close(listenfd);
        return 1;
    }
    //rozpoczęcie nasłuchiwania
    if (listen(listenfd, 10) < 0) {
        perror("listen");
        close(listenfd);
        return 1;
    }

    printf("Serwer gry Double uruchomiony na porcie %d...\n", PORT);

    while (1) {
        //w pętli oczekujemy na nowe połączenie
        connfd = accept(listenfd, (struct sockaddr *)NULL, NULL);
        if (connfd < 0) {
            perror("accept");
            continue;
        }

        int should_broadcast_lobby = 0;
        int should_start_game = 0;
        
        pthread_mutex_lock(&clients_mutex);
        
        //czy mieści się gracz
        int found_slot = -1;
        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (clients[i] == NULL) {
                found_slot = i;
                break;
            }
        }
            
        
        // czy gra się zaczyna
        if (found_slot != -1 && !game_started) {
            // Jest miejsce - tworzymy gracza
            player_t *new_player = malloc(sizeof(player_t));
            new_player->socket = connfd;
            new_player->id = found_slot;
            clients[found_slot] = new_player;
            client_count++;
            new_player->used_cards = 0;

            //tworzy wątek gracz
            pthread_create(&thread_id, NULL, connection_handler, (void *)new_player);
            pthread_detach(thread_id);

            // Informujemy wszystkich o nowym graczu
            should_broadcast_lobby = 1;

            //rozpoczecie gry generacja kart dla graczy na stół i wysłanie kart
            if (client_count == MAX_CLIENTS && !game_started) {

                game_started = 1;
                game_number++;
                srand((unsigned int)time(NULL) ^ (unsigned int)getpid() ^ (unsigned int)(game_number * 7919));
                generate_dobble(); //generacja wszystkich kart
                shuffle_deck_order();

                generate_table_card(); // generacja karty na stole

                should_start_game = 1;
            }
        } 
        else {
            // BRAK MIEJSCA
            char *msg = "ERROR: Gra juz trwa albo serwer jest pelny. Sprobuj pozniej.\n";
            send_to_client(connfd, msg, strlen(msg));
            close(connfd); // Rozłączamy klienta
            printf("Odrzucono połączenie: serwer pełny.\n");
        }
        
        pthread_mutex_unlock(&clients_mutex);

        if (should_broadcast_lobby) {
            broadcast_lobby_status();
        }

        if (should_start_game) {
            printf("START GRY!\n");
            broadcast_card_on_table(table_card);
        }
    }

    return 0;
}
