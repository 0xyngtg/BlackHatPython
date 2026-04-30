import socket

TARGET_HOST : str = '127.0.0.1'
TARGET_PORT : int = 9998

def tcp_client(host : str, port : int) -> str | None:
    #creating a socket object
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #connect the client
    client.connect((host, port))

    #send data
    client.send(b'GET / HTTP/1.1\r\nHost: google.com\r\n\r\n')

    #receive data
    response = client.recv(4096)

    client.close()
    return response.decode()

def main() -> None:
    response = tcp_client(TARGET_HOST, TARGET_PORT)
    print(response)


if __name__ == '__main__':
    main()
