import argparse
import logging
import queue
import threading
from dataclasses import dataclass
from pathlib import Path

import requests

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
LOGGER: logging.Logger = logging.getLogger(__name__)

words_queue: queue.Queue = queue.Queue()

def arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    args: argparse.Namespace = parser.parse_args()
    return args

def filter_status(response:requests.Response, path:str, config:Config) -> bool|None:
    if response.status_code != 404:
        if config.recursive:
            if response.status_code == 200 and path.endswith('/'):
                extend_wordlist(wordlist=config.wordlist, extensions=config.extensions, dir=f'{path}')
        return True
    else:
        return False

def queuer(words_queue:queue.Queue, word:str, extensions:list[str]) -> None:
    for ext in extensions:
        words_queue.put(f'/{word}{ext}')
    if '.' in word:
        words_queue.put(f'/{word}')
    else:
        words_queue.put(f'/{word}/')

def extend_wordlist(wordlist:Path, extensions:list[str], dir:str='') -> queue.Queue:
    with open(wordlist, 'r') as wl:
        words: str = wl.read()
        words_list: list[str] = words.split()

        for word in words_list:
            if dir:
                word : str = dir + word
            queuer(words_queue, word, extensions)
    return words_queue
#

def sender(words_queue:queue.Queue, config:Config) -> None:
    headers: dict[str, str] = {'User-Agent': config.user_agent}

    while not words_queue.empty():
        additional: str = str(words_queue.get())
        url: str = config.target + additional
        response: requests.Response = requests.get(headers=headers, url=url)

        if filter_status(response, path=additional, config=config):
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
    args: argparse.Namespace = arguments()

    config: Config = Config(
        user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:19.0) Gecko/20100101 Firefox/19.0',
        extensions=['.php', '.bak', '.inc', '.orig'],
        threads=50,
        wordlist=Path('C:/Users/Asus/Desktop/ZedProjects/BlackHatPython/WebHackery/test.txt'),
        target='http://127.0.0.1:8081',
        recursive= True
    )

    words_queue: queue.Queue = extend_wordlist(wordlist=config.wordlist, extensions=config.extensions)

    for _ in range(config.threads):
        t: threading.Thread = threading.Thread(target=sender, args=[words_queue, config])
        t.start()

if __name__ == '__main__':
    main()
