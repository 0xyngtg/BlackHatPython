#To use with Linux
from scapy.all import IP, TCP, sniff

MAIL_FILTER = 'tcp port 110 or tcp port 25 or tcp port 143'
#FTP_FILTER = 'tcp port 21'

def packet_callback(packet) -> None:
    if packet[TCP].payload:
        mypacket = str(packet[TCP].payload)
        if 'user' in mypacket.lower() or 'pass' in mypacket.lower():
            print(f'Destionation: {str(packet[IP].dst)}')
            print(f'Payload: {str(packet[IP].payload)}')

def main() -> None:
    sniff(filter=MAIL_FILTER, prn=packet_callback, store=0)

if __name__ == '__main__':
    main()
