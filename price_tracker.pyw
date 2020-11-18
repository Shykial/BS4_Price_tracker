import requests
from bs4 import BeautifulSoup
from sqlite_handler import SQLite
import email_handler
import time
import re
from concurrent.futures import ThreadPoolExecutor
from email_secrets import receiver_address


def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        print(f'Function "{func.__name__}" took {time.time() - start_time} to execute')
        return result

    return wrapper


def get_domain_from_url(url: str) -> str:
    if 'x-kom.pl' in url:
        return 'x-kom'
    if 'delkom.pl' in url:
        return 'delkom'


def get_price_from_soup(soup: BeautifulSoup, domain: str) -> float:
    data = {'x-kom': {'elem_type': 'div', 'class_name': 'u7xnnm-4 iVazGO'},
            'delkom': {'elem_type': 'span', 'class_name': 'price'}}
    elem_type = data[domain]['elem_type']
    class_name = data[domain]['class_name']

    price_text = soup.find(elem_type, attrs={'class': class_name}).get_text()
    price = price_text.removesuffix(' zł')
    return float(price.replace(' ', '').replace(',', '.'))


def get_name_from_soup(soup: BeautifulSoup, domain: str) -> str:
    data = {'x-kom': {'elem_type': 'h1', 'class_name': 'sc-1x6crnh-5 cYILyh'},
            'delkom': {'elem_type': 'h1', 'class_name': 'columns twelve'}}
    elem_type = data[domain]['elem_type']
    class_name = data[domain]['class_name']

    plain_text = soup.find(elem_type, attrs={'class': class_name}).get_text().strip()
    return re.sub(r'\s{2,}', ' ', plain_text)


def get_content_from_url(url: str) -> bytes:
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'}
    r = requests.get(url, headers=headers)
    return r.content


def get_soup_from_contents(contents: str, parse_type='lxml') -> BeautifulSoup:
    return BeautifulSoup(contents, parse_type)


@timer
def main():
    sqlite = SQLite('prices.db')
    urls = ['https://www.x-kom.pl/p/602042-notebook-laptop-156-lenovo-legion-5-15-ryzen-5-32gb-512-gtx1650-120hz.html',
            'https://www.x-kom.pl/p/599019-notebook-laptop-156-lenovo-legion-5-15-ryzen-5-32gb-512-gtx1650ti-144hz.html',
            'https://www.delkom.pl/p/67116-laptop-lenovo-legion-5-15arh05-82b500ampb-16gb-ryzen-7-4800h-156fhd144hz-16gb-512ssd-gtx1650-noos.html',
            'https://www.delkom.pl/p/67130-laptop-lenovo-legion-5-15arh05-82b500ampb-16gb-250ssd-ryzen-7-4800h-156fhd144hz-16gb-512ssd-250ssd-gtx1650-noos.html',
            'https://www.delkom.pl/p/67133-laptop-lenovo-legion-5-15arh05-82b500ampb-16gb-500ssd-ryzen-7-4800h-156fhd144hz-16gb-512ssd-500ssd-gtx1650-noos.html']

    with ThreadPoolExecutor() as executor:
        contents = executor.map(get_content_from_url, urls)

    laptops = {url: {'name': f'{domain} - {get_name_from_soup(soup, domain)}',
                     'price': get_price_from_soup(soup, domain)}
               for url, soup, domain in zip(urls, map(get_soup_from_contents, contents),
                                            map(get_domain_from_url, urls))}

    for url, details in laptops.items():
        new_lowest = sqlite.is_lower_than_table_min(details['name'], details['price'])
        sqlite.insert_data(details['name'], details['price'])

        if new_lowest:
            previous_lowest = new_lowest[1]
            email_subject = f'{details["name"]} just lowered to {details["price"]}zł!'
            email_body = f'''{details["name"]} 
just got its price cut down from {previous_lowest} zł to {details["price"]} zł

For more details visit
{url}'''
            email_handler.send_email(receiver_address, subject=email_subject, body=email_body)
            print('email sent')


if __name__ == '__main__':
    main()
