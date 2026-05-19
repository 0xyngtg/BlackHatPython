import argparse
import logging
import queue
import threading
from dataclasses import dataclass
from pathlib import Path

import requests

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
LOGGER: logging.Logger = logging.getLogger(__name__)

words_queue = queue.Queue()

def arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    args: argparse.Namespace = parser.parse_args()
    return args

def filter_status(response: requests.Response, path: str, recursive: bool) -> bool|None:
    if response.status_code != 404:
        if recursive:
            if response.status_code == 200 and path.endswith('/'):
                words_queue.put(f'{path}')
        return True
    else:
        return False

def extend_wordlist(wordlist, extensions) -> None:
    with open(wordlist) as wl:
        words: str = wl.read()
        words_list:list[str] = words.split()

        for word in words_list:
            for ext in extensions:
                words_queue.put(f'/{word}.{ext}')
            if '.' in word:
                words_queue.put(f'/{word}')
            else:
                words_queue.put(f'/{word}/')

def sender(config:Config, resume=None) -> None:
    headers: dict[str, str] = {'User-Agent': config.user_agent}

    while not words_queue.empty():
        additional: str = str(words_queue.get())
        url: str = config.target + additional
        response: requests.Response = requests.get(headers=headers, url=url)

        if filter_status(response, path= additional, recursive= config.recursive):
            LOGGER.info(f'{url} => {response.status_code}')

@dataclass
class Config:
    user_agent: str
    extensions: list[str]
    threads: int
    wordlist: Path
    target: str
    recursive: bool

def main() -> None:
    args : argparse.Namespace = arguments()

    config: Config = Config(
        user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:19.0) Gecko/20100101 Firefox/19.0',
        extensions=['.php', '.bak', '.inc', '.orig'],
        threads=50,
        wordlist=Path(''),
        target='',
        recursive= True
    )

    extend_wordlist(wordlist=config.wordlist, extensions=config.extensions)

    for _ in range(config.threads):
        t : threading.Thread = threading.Thread(target=sender, args=[config])
        t.start()

if __name__ == '__main__':
    main()
