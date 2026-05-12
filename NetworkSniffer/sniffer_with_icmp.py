import os
import socket
import struct
import sys
from ctypes import Structure, c_ubyte, c_uint32, c_ushort


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

    def __init__(self, socket_buffer=None):
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
            print(f'No protocol for {self.protocol_num}: {e}')

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

    def __init__(self, socket_buffer=None):
        self.sum = socket.ntohs(self.sum)
        self.id  = socket.ntohs(self.id)
        self.seq = socket.ntohs(self.seq)

def sniff(host):
    if os.name == 'nt':
        socket_protocol = socket.IPPROTO_IP
    else:
        socket_protocol = socket.IPPROTO_ICMP
    sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket_protocol)
    sniffer.bind((host, 0))
    sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    if os.name == 'nt':
        sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
    try:
        while True:
            raw_buffer = sniffer.recvfrom(65535)[0]
            ip_header = IP(raw_buffer[0:20])
            if ip_header.protocol == 'ICMP':
                print(f'Protocol: {ip_header.protocol}: {ip_header.src_address} -> {ip_header.dst_address}')
                print(f'Version: {ip_header.ver}')
                print(f'Header Length: {ip_header.ihl}\nTTL: {ip_header.ttl}')
                offset : int = ip_header.ihl * 4
                buf = raw_buffer[offset : offset + 8]
                icmp_header = ICMP(buf)
                print(f'ICMP -> Type: {icmp_header.type} Code: {icmp_header.code}')

    except Exception as e:
        print(e)
        if os.name == 'nt':
            sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
            pass
    except KeyboardInterrupt:
        if os.name == 'nt':
            sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        sys.exit(1)

def main() -> None:
    if len(sys.argv) == 2:
        host = sys.argv[1]
    else:
        host = '192.168.1.67'
    sniff(host)

if __name__ == '__main__':
    main()
