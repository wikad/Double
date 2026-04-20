#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <pthread.h>

#define MAX_CLIENTS 4
#define PORT 8000
#define CARDS_PER_PLAYER 10

 
#define N 7
#define MAX_SYMBOLS (N*N + N + 1)
#define CARDS (N*N + N + 1)
#define SYMBOLS_PER_CARD (N + 1)

int player_cards[MAX_CLIENTS][CARDS_PER_PLAYER][SYMBOLS_PER_CARD]; //id gracza, numer karty, symbol na karcie
int table_card[SYMBOLS_PER_CARD]; // karta w centrum stolu
int cards[CARDS][SYMBOLS_PER_CARD];
// Struktura gracza
typedef struct {
    int socket;
    int id;
    int is_ready;
    int used_cards;
} player_t;

player_t *clients[MAX_CLIENTS];
int client_count = 0;
pthread_mutex_t clients_mutex = PTHREAD_MUTEX_INITIALIZER;

// SZYMON tu jest algorytm dający karty nie wiem jak go zrobic więc powodzenia 
// chyba że jakos inaczej to wymyślisz powodzenia 
int cards[CARDS][SYMBOLS_PER_CARD];

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

void generate_deck_for_player(int player_id) { 
    
    int start = player_id * CARDS_PER_PLAYER;

    for (int i = 0; i < CARDS_PER_PLAYER; i++) {

        for (int j = 0; j < SYMBOLS_PER_CARD; j++) {

            player_cards[player_id][i][j] =cards[start + i][j];
        }
    }
}

// Funkcja do wysyłania wiadomości do wszystkich o oczekiwaniu w lobby taki starterek
void broadcast_lobby_status() {
    char buffer[128];
    pthread_mutex_lock(&clients_mutex);
    
    sprintf(buffer, "LOBBY_UPDATE: Graczy w lobby: %d/%d\n", client_count, MAX_CLIENTS);
    
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i] != NULL) {
            write(clients[i]->socket, buffer, strlen(buffer));
        }
    }
    pthread_mutex_unlock(&clients_mutex);
}

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

    write(p->socket, buffer, strlen(buffer));
}
void generate_table_card()
{
    for (int i = 0; i < SYMBOLS_PER_CARD; i++) {
        table_card[i] = cards[0][i];
    }
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
            write(clients[i]->socket, buffer, strlen(buffer));
        }
    }
    
    pthread_mutex_unlock(&clients_mutex);
}
int symbol_matches_table(int symbol)
{
    for(int i=0; i<SYMBOLS_PER_CARD; i++)
    {
        if(table_card[i]==symbol)
            return 1;
    }
    return 0;
}

void *connection_handler(void *arg) {
    player_t *p = (player_t *)arg;
    char buffer[2048];
    int read_size;

    // --- HANDSHAKE 1: Nadanie ID ---
    sprintf(buffer, "WELCOME: Twoje ID to %d\n", p->id);
    write(p->socket, buffer, strlen(buffer));

    // Informujemy wszystkich o nowym graczu
    broadcast_lobby_status();

    // Symulacja oczekiwania na start gry (np. gdy uzbiera się 2 graczy)
    //W grze musi być oczekiwanie na drugi handshake 
    
    /* --- HANDSHAKE 2: Start gry ---
       Wysłanie tablicy kart po wywołaniu generate_deck_for_player() SZYMON
       Troche nie wiem jak przesłąć tablice kart ale jakoś to pójdzie no chyba że nie bezie miał gracz swoich kart tylko będą na serwerze 
    */
   //to czeka nwm czy tego nie usunąć 
   
   
    while(1) {
        pthread_mutex_lock(&clients_mutex);
        if (client_count >= MAX_CLIENTS) { 
            pthread_mutex_unlock(&clients_mutex);
            break; 
        }
        pthread_mutex_unlock(&clients_mutex);
        usleep(100000); // Śpij 0.1s, żeby nie męczyć procesora
    }
    sprintf(buffer, "GAME_START: Twoje karty: [MIEJSCE NA LOGIKE]\n");
    write(p->socket, buffer, strlen(buffer));

    // --- GŁÓWNA PĘTLA GRY ---
    while ((read_size = recv(p->socket, buffer, sizeof(buffer) - 1, 0)) > 0) {
        buffer[read_size] = '\0';
        /*
        if(buffer == oneofcardontable())
        {
             LOGIKA BROADCASTU KARTY ZE STOŁU
            Jeśli klient przyśle dopasowanie, tutaj następuje walidacja
            i ewentualny broadcast nowej karty stołu do wszystkich.
            sprintf(buffer, "YOUR_CARDS: [MIEJSCE NA LOGIKE]\n");
            write(p->socket, buffer, strlen(buffer));
            to jest do odesłania jego kart nowych 
            PLUS BROADCAST NOWEJ KARTY NA STOLE DO WSZYSTKICH
            broadcast_card_on_table(new_card);
        }
        else{
            sprintf(buffer, "NOT_ON_TABLE\n");
            write(p->socket, buffer, strlen(buffer));
        }
        */

        if (strncmp(buffer, "PLAY:", 5) == 0) {
        int symbol = atoi(buffer + 5);

        if (symbol_matches_table(symbol)) {
            
            for (int i=0; i<SYMBOLS_PER_CARD; i++)
            {
                table_card[i]=player_cards[p->id][p->used_cards][i];
            }
            p->used_cards++;
            broadcast_card_on_table(table_card); 
        } else {
            write(p->socket, "NOT_ON_TABLE\n", 13);
        }
    }

        usleep(40000);
        // Tymczasowy log dla testów
        printf("Gracz %d wysłał ruch: %s", p->id, buffer);
        
        memset(buffer, 0, 2048);
    }

    // Rozłączenie
    printf("Gracz %d opuścił grę.\n", p->id);
    close(p->socket);
    
    pthread_mutex_lock(&clients_mutex);
    clients[p->id] = NULL;
    client_count--;
    pthread_mutex_unlock(&clients_mutex);
    
    broadcast_lobby_status();
    free(p);
    return NULL;
}

int main() {

    //to jest prawie to co w templatce ale dodałem tam logikę związaną z ograniczeniem liczby graczy tak o 
    int listenfd, connfd;
    struct sockaddr_in serv_addr;
    pthread_t thread_id;

    listenfd = socket(AF_INET, SOCK_STREAM, 0);
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    serv_addr.sin_port = htons(PORT);

    bind(listenfd, (struct sockaddr *)&serv_addr, sizeof(serv_addr));
    listen(listenfd, 10);

    printf("Serwer gry Double uruchomiony na porcie %d...\n", PORT);

    int game_started=0; //wartownik

    while (1) {
        connfd = accept(listenfd, (struct sockaddr *)NULL, NULL);
        
        pthread_mutex_lock(&clients_mutex);
        
        // Taki komunikat zrobiony jest na szybko żeby jak nie będzie miejsca to klient dostanie info że serwer jest pełny i się rozłączy
        int found_slot = -1;
        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (clients[i] == NULL) {
                found_slot = i;
                break;
            }
        }

        if (found_slot != -1) {
            // Jest miejsce - tworzymy gracza
            player_t *new_player = malloc(sizeof(player_t));
            new_player->socket = connfd;
            new_player->id = found_slot;
            clients[found_slot] = new_player;
            client_count++;
            new_player->used_cards = 0;
            //rozpoczecie gry generacja kart dla graczy na stół i wysłanie kart
            if (client_count == MAX_CLIENTS && !game_started) {

                game_started = 1;
                printf("START GRY!\n");

                generate_dobble(); //generacja wszystkich kart

                generate_table_card(); // generacja karty na stole

                broadcast_card_on_table(table_card);

                // wyślij karty graczy
                for (int i = 0; i < MAX_CLIENTS; i++) {
                    if (clients[i] != NULL) {
                        send_player_cards(clients[i]);
                    }
                }
            }
            
            pthread_create(&thread_id, NULL, connection_handler, (void *)new_player);
        } else {
            // BRAK MIEJSCA
            char *msg = "ERROR: Serwer jest pelny. Sprobuj pozniej.\n";
            write(connfd, msg, strlen(msg));
            close(connfd); // Rozłączamy klienta
            printf("Odrzucono połączenie: serwer pełny.\n");
        }
        
        pthread_mutex_unlock(&clients_mutex);
    }

    return 0;
}