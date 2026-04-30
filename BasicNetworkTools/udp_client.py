import socket

TARGET_HOST : str = '127.0.0.1'
TARGET_PORT : int = 9997

def udp_client(host : str, port : int) -> str:
    #socket object
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    #send data
    client.sendto(b'AAABBBCCC', (host, port))

    #receive some data
    data, addr = client.recvfrom(4096)

    client.close()
    return data.decode()

def main() -> None:
    response = udp_client(TARGET_HOST, TARGET_PORT)
    print(response)


if __name__ == '__main__':
    main()
