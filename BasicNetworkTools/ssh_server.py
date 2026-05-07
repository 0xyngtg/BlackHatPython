import logging
import os
import socket
import threading

import paramiko

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

CWD = os.path.dirname(os.path.realpath(__file__))
HOSTKEY = paramiko.RSAKey(filename=os.path.join(CWD, 'test_rsa.key'))


class Server(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind=='session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if (username == 'johndoe') and (password == 'pass'):
            return paramiko.AUTH_SUCCESSFUL

def main() -> None:
    server = '127.0.0.1'
    ssh_port = 2222
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((server, ssh_port))
        sock.listen(100)
        logger.info('Listening for connection...')
        client, addr = sock.accept()
    except Exception as e:
        print(f'Listen failed: {str(e)}')
        return
    else:
        logger.info(f'Got a connection {client} - {addr[0]}:{addr[1]}')

    session = paramiko.Transport(client)
    session.add_server_key(HOSTKEY)
    server = Server()
    session.start_server(server=server)

    chan = session.accept(20)
    if chan is None:
        logger.error('No channel.')
        return

    logger.info('Authenticated!')
    logger.info(chan.recv(1024))
    try:
        while True:
            command = input('> ')
            while command == "":
                command = input('> ')
            if command != 'exit':
                chan.send(command.encode())
                response = chan.recv(8192)
                logger.info(response.decode(errors='replace'))
            else:
                chan.send('exit'.encode())
                logger.warning('Exiting...')
                session.close()
                break
    except KeyboardInterrupt:
        session.close()

if __name__ == '__main__':
    main()
