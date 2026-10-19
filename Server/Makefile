CFLAGS = -O2 -Wall -Wextra

dobble_server: Server.c
	$(CC) $(CFLAGS) -o $@ Server.c -lpthread

clean:
	rm -f dobble_server
