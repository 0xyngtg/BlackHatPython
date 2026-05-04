import socket
import threading

IP = '0.0.0.0'
PORT = 9002

def tcp_server(ip : str, port : int) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.bind((IP, PORT))

    server.listen(5)

    while True:
        client, addr = server.accept()
        print(f'[!] Accepted connection from {addr[0]}:{addr[1]}...')

        client_handler = threading.Thread(target=handle_client, args=(client,))
        client_handler.start()

def handle_client(client_socket : socket.socket) -> None:
    with client_socket as sock:
        request = sock.recv(1024)
        print(f'[!] Received: {request.decode('utf-8')}')
        sock.send(b'ACK')

def main() -> None:
    tcp_server(IP, PORT)


if __name__ == '__main__':
    main()
