import logging
import os
import socket
import threading

import paramiko

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

CWD : str = os.path.dirname(os.path.realpath(__file__))
HOSTKEY : paramiko.RSAKey = paramiko.RSAKey(filename=os.path.join(CWD, 'test_rsa.key'))

class Server(paramiko.ServerInterface):
    def __init__(self, ip, port):
        self.event = threading.Event()
        self.ip : str = ip
        self.port : int = port

    def check_channel_request(self, kind, chanid):
        if kind=='session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if (username == 'johndoe') and (password == 'pass'):
            return paramiko.AUTH_SUCCESSFUL

    def set_server(self) -> None:
        try:
            sock : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.ip, self.port))
            sock.listen(100)
            logger.info('Listening for connection...')
            client, addr = sock.accept()
            logger.info(f'Got a connection {client} - {addr[0]}:{addr[1]}')

            session = paramiko.Transport(client)
            session.add_server_key(HOSTKEY)
            session.start_server(server=self)

            chan : paramiko.Channel | None = session.accept(20)
            if chan is None:
                logger.error('No channel.')
                return

            logger.info('Authenticated!')
            logger.info(chan.recv(1024))

            while True:
                command = input('> ')
                if command == "":
                    continue
                if command != 'exit':
                    chan.send(command.encode())
                    response = chan.recv(8192)
                    logger.info(response.decode(errors='replace'))
                else:
                    chan.send(b'exit')
                    session.close()
                    break
        except KeyboardInterrupt:
            logger.info('Interrupted by user.')
        except Exception as e:
            logger.error(f'Error: {str(e)}')

def main() -> None:
    server = Server(ip='127.0.0.1', port=2222)
    server.set_server()

if __name__ == '__main__':
    main()
