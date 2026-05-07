import logging

import paramiko

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def ssh_command(ip, port, user, passwd, cmd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, port=port, username=user, password=passwd)

    _, stdout, stderr = client.exec_command(cmd)
    output = stdout.readlines() + stderr.readlines()
    if output:
        logger.info(f'Output:')
        for line in output:
            logger.info(f'>> {line.strip()}')

def main() -> None:
    import getpass
    user = getpass.getuser()
    passwd = getpass.getpass()
    ip = input('Enter server IP: ')
    port = input('Enter port or <CR>: ') or 2222
    cmd = input('Enter command or <CR>: ') or 'id'

    ssh_command(ip, port, user, passwd, cmd)

if __name__ == '__main__':
    main()
