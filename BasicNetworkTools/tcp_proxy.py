import argparse
import logging
import socket
import threading
from dataclasses import dataclass

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger()

def arguments() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='tcp_proxy')
    parser.add_argument('-lh', required= True, type=str, help='Local host')
    parser.add_argument('-lp', required= True, type=int, help='Local port')
    parser.add_argument('-rh', required= True, type=str, help='Remote host')
    parser.add_argument('-rp', required= True, type=int, help='Remote port')
    parser.add_argument('--receive', action='store_true', help='Receive first')
    return parser

HEX_FILTER = ''.join(
    [(len(repr(chr(i))) == 3) and chr(i) or '.' for i in range(256)]
)

def hexdump(src:str|bytes, length:int=16, show:bool=True):
    if isinstance(src, bytes):
        src.decode()

    results = []
    for i in range(0, len(src), length):
        word = str(src[i:i+length])
        printable = word.translate(HEX_FILTER)
        hexa = ' '.join([f'{ord(c):02X}' for c in word])
        hexwidth = length * 3
        results.append(f'{i:04x}    {hexa:<{hexwidth}}{printable}')
        if show:
            for line in results:
                print(line)
        else:
            return results

def receive_from(connection) -> bytes:
    buffer : bytes = b''
    connection.settimeout(5)
    try:
        while True:
            data = connection.recv(4096)
            if not data:
                break
            buffer += data
    except Exception as e:
        pass
    return buffer

@dataclass
class Proxy:
    server : tuple[str, int]
    remote : tuple[str, int]
    receive_first : bool = False

    def server_connection(self) -> socket.socket:
        try:
            server_socket : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind((self.server))
            logger.info(f'Listening on {self.server[0]}:{self.server[1]}')
            return server_socket
        except Exception as e:
            logger.error(f'Problem on bind: {e}\n [X] Failed to listen on {self.server[0]}{self.server[1]} - Check for other listening sockets or correct permissions.')
            return

    def remote_connection(self) -> socket.socket:
        remote_socket : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect(self.remote)
        return remote_socket

    def request_handler(self, buffer) -> bytes:
        return buffer

    def response_handler(self, buffer) -> bytes:
        return buffer

    def main_handler(self, client_socket:socket.socket, remote_socket:socket.socket, receive_first:bool) -> None:
        if receive_first:
            remote_buffer : bytes = receive_from(remote_socket)
            hexdump(remote_buffer)

        remote_buffer = self.response_handler(remote_buffer)
        if len(remote_buffer):
            logger.info(f'[<==] Sending {len(remote_buffer)} bytes to localhost.')
            client_socket.send(remote_buffer)

        while True:
            local_buffer : bytes = receive_from(client_socket)
            if len(local_buffer):
                logger.info(f'[==>] Received {len(local_buffer)} bytes from localhost.')
                hexdump(local_buffer)
                local_buffer = self.request_handler(local_buffer)
                remote_socket.send(local_buffer)
                logger.info('[==>] Sent to remote.')

            remote_buffer = receive_from(remote_socket)

            if len(remote_buffer):
                logger.info(f'[<==] Received {len(remote_buffer)} bytes from remote.')
                hexdump(remote_buffer)
                remote_buffer = self.response_handler(remote_buffer)
                client_socket.send(remote_buffer)
                logger.info('[<==] Sent to localhost.')

            if not len(local_buffer) or not len(remote_buffer):
                client_socket.close()
                remote_socket.close()
                logger.warning('No more data. Closing connections.')
                break

    def server_loop(self, server_socket:socket.socket, remote_socket:socket.socket) -> None:
        server_socket.listen(5)

        while True:
            client_socket, addr = server_socket.accept()
            logger.info(f'Received incoming connection from {addr[0]}{addr[1]}')

            proxy_thread = threading.Thread(
                target=self.main_handler,
                args=(client_socket, remote_socket, self.receive_first)
            )
            proxy_thread.start()



def main() -> None:
    parser : argparse.ArgumentParser = arguments()
    #args : argparse.Namespace = parser.parse_args()

    ###test
    test_args=['-lh', '127.0.0.1', '-lp', '9001', '-rh', '127.0.0.1', '-rp', '9002', '--receive']
    args = parser.parse_args(test_args)
    ###

    proxy = Proxy(
        server = (args.lh, args.lp),
        remote = (args.rh, args.rp),
        receive_first = args.receive
    )

    server_socket : socket.socket = proxy.server_connection()
    remote_socket : socket.socket = proxy.remote_connection()

    proxy.server_loop(server_socket, remote_socket)

if __name__ == '__main__':
    main()
