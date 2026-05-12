import ipaddress
import os
import socket
import struct
import threading
import time
from ctypes import Structure, c_ubyte, c_uint32, c_ushort

SUBNET : str = '192.168.1.0/24'
MESSAGE : str = 'testtttttt123'

def set_socket(host : str) -> socket.socket:
    if os.name == 'nt':
        socket_protocol : int = socket.IPPROTO_IP
    else:
        socket_protocol = socket.IPPROTO_ICMP

    sock : socket.socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_RAW,
        socket_protocol
    )

    sock.bind((host, 0))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

    if os.name == 'nt':
        sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)

    time.sleep(5)

    return sock

def udp_sender() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        for ip in ipaddress.ip_network(SUBNET).hosts():
            sender.sendto(
                bytes(MESSAGE, 'utf8'),
                (str(ip), 65212)
            )

def ip_decode(raw_buffer : bytes) -> IP:
    ip_header : IP = IP(raw_buffer[0:20])
    return ip_header

def ip_operation(ip_header : IP, raw_buffer : bytes, hosts_up) -> None:
    src_address : ipaddress.IPv4Address = ipaddress.ip_address(ip_header.src_address)
    subnet_network : ipaddress.IPv4Network = ipaddress.IPv4Network(SUBNET)

    if ip_header.protocol == 'ICMP' and src_address in subnet_network and raw_buffer[len(raw_buffer) - len(MESSAGE):] == bytes(MESSAGE, 'utf8'):
        icmp_header = icmp_decode(ip_header, raw_buffer)
        icmp_operation(ip_header, icmp_header, hosts_up)
    else:
        return

def icmp_decode(ip_header : IP, raw_buffer : bytes) -> ICMP:
    offset : int = ip_header.ihl * 4
    buffer = raw_buffer[offset : offset + 8]
    icmp_header = ICMP(buffer)
    return icmp_header

def icmp_operation(ip_header : IP, icmp_header : ICMP, hosts_up : set[str]) -> None:
    if icmp_header.code == 3 and icmp_header.type == 3:
        host_up : str = str(ip_header.src_address)
        if host_up not in hosts_up:
            hosts_up.add(host_up)

class Scanner:
    def __init__(self, host):
        self.host = host
        self.sock = set_socket(self.host)

    def sniff(self):
        end_time = time.time() + 60
        hosts_up : set[str] = set()
        try:
            while time.time() < end_time:
                raw_buffer : bytes = self.sock.recvfrom(65535)[0]
                ip_header : IP = ip_decode(raw_buffer)
                ip_operation(ip_header, raw_buffer, hosts_up)
        except KeyboardInterrupt:
            print('\nUser Interrupted!')
        finally:
            if os.name == 'nt':
                self.sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
            if hosts_up:
                print(f'Hosts up on {SUBNET}:')
                for host in sorted(hosts_up):
                    print(f'{host}')

class IP(Structure):
    _pack_ = 1
    _fields_ = [
        ('ihl', c_ubyte, 4),
        ('ver', c_ubyte, 4),
        ('tos', c_ubyte, 8),
        ('len', c_ushort, 16),
        ('id', c_ushort, 16),
        ('offset', c_ushort, 16),
        ('ttl', c_ubyte, 8),
        ('protocol_num', c_ubyte, 8),
        ('sum', c_ushort, 16),
        ('src_addr', c_uint32, 32),
        ('dst_addr', c_uint32, 32)
    ]

    def __new__(cls, socket_buffer=None):
        return cls.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer=None) -> None:
        self.src_address = socket.inet_ntoa(struct.pack('<L', self.src_addr))
        self.dst_address = socket.inet_ntoa(struct.pack('<L', self.dst_addr))
        self.protocol_map = {
            1 : 'ICMP',
            6 : 'TCP',
            17 : 'UDP'
        }
        try:
            self.protocol = self.protocol_map[self.protocol_num]
        except Exception as e:
            self.protocol = None
            #print(f'No protocol for {self.protocol_num}: {e} -- from {self.src_address}')
            return

class ICMP(Structure):
    _pack_ = 1
    _fields_ = [
        ('type', c_ubyte),
        ('code', c_ubyte),
        ('sum', c_ushort),
        ('id', c_ushort),
        ('seq', c_ushort)
    ]

    def __new__(cls, socket_buffer=None):
        return cls.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer=None) -> None:
        self.sum = socket.ntohs(self.sum)
        self.id  = socket.ntohs(self.id)
        self.seq = socket.ntohs(self.seq)

def main() -> None:
    host = '192.168.1.67'
    s = Scanner(host)
    t = threading.Thread(target=udp_sender)
    t.start()
    s.sniff()

if __name__ == '__main__':
    main()
