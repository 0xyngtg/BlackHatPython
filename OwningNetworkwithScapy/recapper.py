import collections
import os
import re
import sys
import zlib
from pathlib import Path

from scapy.all import TCP, rdpcap

OUTDIR : Path = Path('/root/Desktop/pictures')
PCAPS : Path = Path('/root/Downloads')

Response = collections.namedtuple('Response',
    [
        'header',
        'payload'
    ])

def get_header(raw_response:bytes) -> dict[str, str] | None:
    try:
        header_raw : bytes = raw_response[:raw_response.index(b'\r\n\r\n')+2]
    except ValueError:
       sys.stdout.write('-')
       sys.stdout.flush()
       return None

    header : dict[str, str] = dict(re.findall(r'(?P<name>.*?): (?P<value>.*?)\r\n', header_raw.decode()))
    if 'Content-Type' not in header:
        return None
    return header

def extract_content(Response, content_name='image') -> tuple[bytes, bytes]:
    content, content_type = None, None
    if content_name in Response.header['Content-Type']:
        content_type : bytes = Response.header['Content-Type'].split('/')[1]
        content : bytes = Response.payload[Response.payload.index(b'\r\n\r\n')+4:]

        if 'Content-Encoding' in Response.header:
            if Response.header['Content-Encoding'] == 'gzip':
                content = zlib.decompress(Response.payload, zlib.MAX_WBITS | 32)
            elif Response.header['Content-Encoding'] == 'deflate':
                content = zlib.decompress(Response.payload)
        return content, content_type

class Recapper:
    def __init__(self, fname):
        pcap = rdpcap(fname)
        self.sessions : dict = pcap.sessions()
        self.responses : list[Response] = list()

    def get_responses(self):
        for session in self.sessions:
            payload : bytes = b''

            for packet in self.sessions[session]:
                try:
                    if packet[TCP].dport == 80 or packet[TCP].sport == 80:
                        payload += bytes(packet[TCP].payload)
                except IndexError:
                    sys.stdout.write('x')
                    sys.stdout.flush()
            if payload:
                header = get_header(raw_response=payload)
                if header is None:
                    continue
                self.responses.append(Response(header=header, payload=payload))

    def write(self, content_name:str):
        for i, response in enumerate(self.responses):
            content, content_type = extract_content(response, content_name)
            if content and content_type:
                fname : Path = OUTDIR / f'ex_{i}.{content_type}'
                print(f'Writing {fname}')
                with open(fname, 'wb') as f:
                    f.write(content)

def main() -> None:
    pfile : Path = PCAPS / 'pcap.pcap'
    recapper : Recapper = Recapper(pfile)
    recapper.get_responses()
    recapper.write('image')

if __name__ == '__main__':
    main()
