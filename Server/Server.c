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

// Struktura gracza
typedef struct {
    int socket;
    int id;
    int is_ready;
} player_t;

player_t *clients[MAX_CLIENTS];
int client_count = 0;
pthread_mutex_t clients_mutex = PTHREAD_MUTEX_INITIALIZER;

// SZYMON tu jest algorytm dający karty nie wiem jak go zrobic więc powodzenia 
void generate_deck_for_player(int player_id) {
    
    // Musisz wypełnić tablice kart gracza co późńiej idzie do niego 
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
    sprintf(buffer, "GAME_START: Twoje karty: [MIEJSCE NA LOGIKE]\n");
    write(p->socket, buffer, strlen(buffer));

    // --- GŁÓWNA PĘTLA GRY ---
    while ((read_size = recv(p->socket, buffer, sizeof(buffer) - 1, 0)) > 0) {
        buffer[read_size] = '\0';

        /* LOGIKA BROADCASTU KARTY ZE STOŁU
           Jeśli klient przyśle dopasowanie, tutaj następuje walidacja
           i ewentualny broadcast nowej karty stołu do wszystkich.
        */
        
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