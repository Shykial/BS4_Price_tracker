import requests
from bs4 import BeautifulSoup
from sqlite_handler import SQLite
import time
import re
from concurrent.futures import ThreadPoolExecutor


def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        print(f'Function "{func.__name__}" took {time.time() - start_time} to execute')
        return result

    return wrapper


def get_price_from_soup(soup: BeautifulSoup) -> float:
    class_name = 'u7xnnm-4 iVazGO'
    price_text = soup.find('div', attrs={'class': class_name}).get_text()
    price = price_text.removesuffix(' zł')
    return float(price.replace(' ', '').replace(',', '.'))


def get_name_from_soup(soup: BeautifulSoup) -> str:
    class_name = 'sc-1x6crnh-13 fXjZNH'
    plain_text = soup.find('div', attrs={'class': class_name}).get_text().strip()
    return re.sub(r'\s{2,}', ' ', plain_text)


def get_content_from_url(url: str) -> bytes:
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'}
    r = requests.get(url, headers=headers)
    return r.content


def get_soup_from_contents(contents: str, parse_type='html.parser') -> BeautifulSoup:
    return BeautifulSoup(contents, parse_type)


@timer
def main():
    sqlite = SQLite('prices.db')
    urls = ['https://www.x-kom.pl/p/599015-notebook-laptop-156-lenovo-legion-5-15-ryzen-5-32gb-960-win10-gtx1650.html',
            'https://www.x-kom.pl/p/602042-notebook-laptop-156-lenovo-legion-5-15-ryzen-5-32gb-512-gtx1650-120hz.html',
            'https://www.x-kom.pl/p/599019-notebook-laptop-156-lenovo-legion-5-15-ryzen-5-32gb-512-gtx1650ti-144hz.html',
            'https://www.x-kom.pl/p/599012-notebook-laptop-156-lenovo-legion-5-15-ryzen-5-32gb-480-win10-gtx1650.html']

    with ThreadPoolExecutor() as executor:
        contents = executor.map(get_content_from_url, urls)

    laptops = {url: {'name': get_name_from_soup(soup), 'price': get_price_from_soup(soup)}
               for url, soup in zip(urls, map(get_soup_from_contents, contents))}

    for details in laptops.values():
        sqlite.insert_data(details['name'], details['price'])


if __name__ == '__main__':
    main()
