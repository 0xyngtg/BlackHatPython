import argparse
import shlex
import socket
import subprocess
import sys
import textwrap
import threading
import time
from enum import Enum, auto


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='BHP Net Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            '''
            netcat.py -t <IP> -p <PORT> -l -s #command shell
            netcat.py -t <IP> -p <PORT> -l -u=mytest.py #upload to file
            netcat.py -t <IP> -p <PORT> -l -c="cat /etc/passwd" #execute command
            echo "ABC" | netcat.py -t <IP> -p <PORT> #echo text to server port 135
            netcat.py -t <IP> -p <PORT> #connect to server
            '''
        )
    )
    parser.add_argument('-s', '--shell', action='store_true', help='command shell')
    parser.add_argument('-c', '--command', help='execute specified command')
    parser.add_argument('-l', '--listen', action='store_true', help='listen')
    parser.add_argument('-p', '--port', type=int, default=5555, help='specified port')
    parser.add_argument('-t', '--target', default='127.0.0.1', help='specified IP')
    parser.add_argument('-u', '--upload', help='upload file')
    args = parser.parse_args()
    return args

def execute(cmd : str) -> str | None:
    if cmd :
        cmd = cmd.strip()
    else:
        return

    try:
        output : bytes = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
    except OSError as e:
        return f'[!] Error: Use "cmd /c" to run commands: {e}'
    return output.decode('utf-8')

def shell(client_socket : socket.socket) -> None:
    cmd_buffer = b''
    while True:
        try:
            client_socket.send(b'###')
            while '\n' not in cmd_buffer.decode('utf-8'):
                cmd_buffer += client_socket.recv(64)
            response = execute(cmd_buffer.decode('utf-8'))
            if response:
                client_socket.send(response.encode())
            cmd_buffer = b''
        except Exception as e:
           print(f'[-] Server killed {e}')
           return

def file_upload(client_socket : socket.socket, file : str) -> None:
    file_buffer = b''
    while True:
        data = client_socket.recv(4096)
        if data:
            file_buffer += data
        else:
            break
    with open(file, 'wb') as f:
        f.write(file_buffer)

class ListenMode(Enum):
    SHELL = auto()
    FILE_UPLOAD = auto()
    COMMAND_EXECUTE = auto()

class NetCat:
    def __init__(self, args:argparse.Namespace, buffer:bytes) -> None:
        self.args : argparse.Namespace = args
        self.buffer : bytes = buffer
        self.socket : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def send(self):
        self.socket.connect((self.args.target, self.args.port))
        if self.buffer:
            self.socket.send(self.buffer)

        try:
            while True:
                recv_len = 1
                response = ''
                while recv_len:
                    data = self.socket.recv(4096)
                    recv_len = len(data)
                    response += data.decode()
                    if recv_len < 4096:
                        break
                if response:
                    print(response)
                    buffer = input('> ')
                    buffer += '\n'
                    self.socket.send(buffer.encode())
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print('[-] User terminated.')
            self.socket.close()
            return

    def listen(self, mode : ListenMode):
        self.socket.bind((self.args.target, self.args.port))
        self.socket.listen(5)
        print(f'[+] Listening on {self.args.target}:{self.args.port} (mode: {mode.name})')

        while True:
            client_socket, addr = self.socket.accept()
            print(f'[+] Received a connection from {addr}')
            client_thread = threading.Thread(target=self.handler, args=(client_socket, mode ))
            client_thread.start()

    def handler(self, client_socket, mode):
        if mode == ListenMode.COMMAND_EXECUTE:
            output = execute(self.args.command)
            client_socket.send(output.encode())

        elif mode == ListenMode.FILE_UPLOAD:
            file_upload(client_socket, file=self.args.upload)
            message = f'[+] Saved file {self.args.upload}'
            client_socket.send(message.encode())

        elif mode == ListenMode.SHELL:
            self.mode : ListenMode = ListenMode.SHELL
            shell(client_socket)
            self.socket.close()
            return

def main() -> None:
    args = arguments()
    if args.listen:
        buffer : str = ''
        if args.shell:
            mode = ListenMode.SHELL
        elif args.upload:
            mode = ListenMode.FILE_UPLOAD
        elif args.command:
            mode = ListenMode.COMMAND_EXECUTE
        else:
            print('[!] Select a listen mode: -s, -c, -u')
    else:
        buffer = sys.stdin.read() if not sys.stdin.isatty() else ''

    nc = NetCat(args, buffer.encode())

    if args.listen:
        nc.listen(mode=mode)
    else:
        nc.send()


if __name__ == '__main__':
    main()
