import argparse
import getpass
import logging
import select
import socket
import threading
from dataclasses import dataclass

import paramiko

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

FORWARDED_PORT = 9001

def arguments():
    parser = argparse.ArgumentParser(prog='rforward.py', usage='Access the target service on the localport 9001 on the SSH server system')
    parser.add_argument('-lh', required=True, type=str, help='Local host')
    parser.add_argument('-lp', required=True, type=int, help='Local port')
    parser.add_argument('-rh', required=True, type=str, help='Remote host')
    parser.add_argument('-rp', required=True, type=int, help='Remote port')
    parser.add_argument('-u', required=True, type=str, help='SSH user')
    parser.add_argument('--p', action='store_true', required=False, help='SSH password prompt')
    parser.add_argument('--k', required=False, type=str, help='SSH key file')
    return parser

def connect_SSH(ssh_host:tuple[str, int], ssh_auth:tuple[str, str, str]) -> paramiko.Transport:
    host, port = ssh_host
    username, password, key = ssh_auth

    client : paramiko.SSHClient = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    if key == '':
        key = None

    client.connect(
        hostname=host,
        port=port,
        username=username,
        password=password,
        key_filename=key
    )

    transport : paramiko.Transport = client.get_transport()
    transport.request_port_forward(host, FORWARDED_PORT)
    return transport

def connect_socket(remote_host:tuple[str, int]) -> socket.socket | None:
    r_socket = socket.socket()
    try:
        r_socket.connect(remote_host)
        return r_socket
    except Exception as e:
        logger.error(f'Error connecting to {remote_host}: {e}')

class RForward():
    def __init__(self, transport, r_host):
        self.r_host : tuple[str, int] = r_host
        self.transport : paramiko.Transport = transport

    def handler(self):
        while True:
            ssh_chan = self.transport.accept(1000)
            if ssh_chan is None:
                continue

            r_socket : socket.socket | None = connect_socket(self.r_host)

            logger.info(f'Connected to both ends. Tunneling is starting:\n {ssh_chan.origin_addr} => {ssh_chan.getpeername()} => {self.r_host[0]}:{self.r_host[1]}')

            thr : threading.Thread = threading.Thread(
                target=self.tunnel,
                args=(ssh_chan, r_socket),
                daemon=True
            )
            thr.start()

    def tunnel(self, chan:paramiko.Channel, r_socket:socket.socket):
        while True:
            r, w, x = select.select([chan, r_socket], [], [])
            if chan in r:
                data : bytes = chan.recv(1024)
                if data:
                    r_socket.send(data)
                else:
                    logger.info('No data received from the SSH server!')
                    break
            if r_socket in r:
                data = r_socket.recv(1024)
                if data:
                    chan.send(data)
                else:
                    logger.info('No data received from the remote host!')
                    break
        chan.close()
        r_socket.close()
        logger.warning('Tunnel closed!')
        return

@dataclass
class ConnectionData():
    ssh_host : str
    ssh_port : int
    ssh_username : str
    ssh_password : bool | str | None = None
    ssh_key : str | None = None

    @property
    def auth(self) -> tuple[str, str, str]:
        if self.ssh_password:
            self.ssh_password = getpass.getpass()
            return (self.ssh_username, self.ssh_password, '')
        else:
            return (self.ssh_username, '', self.ssh_key)

    @property
    def host(self) -> tuple[str, int]:
        return (self.ssh_host, self.ssh_port)

def main() -> None:
    parser : argparse.ArgumentParser = arguments()
    args = parser.parse_args()

    ssh_data = ConnectionData(
        ssh_host=args.lh,
        ssh_port=args.lp,
        ssh_username=args.u,
        ssh_password=args.p,
        ssh_key=args.k
    )
    ssh_host : tuple[str, int] = ssh_data.host
    ssh_auth : tuple[str, str, str] = ssh_data.auth
    r_host : tuple[str, int] = (args.rh, args.rp)

    transport : paramiko.Transport = connect_SSH(ssh_host, ssh_auth)

    forwarding = RForward(transport, r_host)
    forwarding.handler()

if __name__ == '__main__':
    main()
