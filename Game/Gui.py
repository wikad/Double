import pygame
import sys

class GUI:
    def __init__(self, client):
        pygame.init()
        self.client = client 
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption(f"Dobble - Gracz {self.client.my_id}")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24)
        self.input_text = "" # symbol od gracza 

    def lobby(self):
            
            while self.client.current_players != self.client.max_players and self.client.max_players > 0:
                self.screen.fill((255, 255, 255))
                waiting_text = self.font.render(f"Czekam na graczy... {self.client.current_players}/{self.client.max_players}", True, (0, 0, 0))
                self.screen.blit(waiting_text, (200, 250))
                pygame.display.flip()
                self.clock.tick(30)
    
    def gameLoop(self):
        running = True
        input_text = "" # Zmienna na wpisywany symbol

        while running:
            # 1. OBSŁUGA ZDARZEŃ (zamiast input)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN: # ENTER wysyła ruch
                        self.client.send_move(input_text)
                        input_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    else:
                        input_text += event.unicode # Dopisywanie liter

            # 2. RYSOWANIE (zamiast print)
            self.screen.fill((255, 255, 255))
            
            if self.client.myCards and self.client.tableCard:
                # Wyświetlanie kart
                txt_stolo = self.font.render(f"Stół: {self.client.tableCard}", True, (0, 0, 0))
                txt_moje = self.font.render(f"Twoja: {self.client.myCards[self.client.obecna_karta]}", True, (0, 0, 200))
                txt_input = self.font.render(f"Wpisz i ENTER: {input_text}", True, (0, 150, 0))
                
                self.screen.blit(txt_stolo, (50, 50))
                self.screen.blit(txt_moje, (50, 100))
                self.screen.blit(txt_input, (50, 200))
            else:
                loading = self.font.render("Czekam na rozdanie kart...", True, (100, 100, 100))
                self.screen.blit(loading, (50, 50))

            pygame.display.flip()
            self.clock.tick(30) # 30 klatek wystarczy

    def close(self):
        self.client.close()
        pygame.quit()
        sys.exit()