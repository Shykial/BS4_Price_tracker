import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

import email_handler
import resources as rs
from email_secrets import receiver_address, debug_receiver_address
from sqlite_handler import SQLite


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
    if 'oleole.pl' in url:
        return 'oleole'
    if 'euro.com.pl' in url:
        return 'euro-rtv-agd'
    if 'amazon.com' in url:
        return 'amazon.com'
    raise AttributeError(f'Domain in url: {url} not recognised')


def get_price_from_soup(soup: BeautifulSoup, domain: str) -> float:
    data = {'x-kom': {'elem_type': 'div', 'class_name': 'u7xnnm-4 iVazGO'},
            'delkom': {'elem_type': 'span', 'class_name': 'price'},
            'oleole': {'elem_type': 'div', 'class_name': 'price-normal selenium-price-normal'},
            'euro-rtv-agd': {'elem_type': 'div', 'class_name': 'product-price'},
            'amazon.com': {'elem_type': 'span', 'id': 'priceblock_ourprice'}}
    elem_type = data[domain]['elem_type']
    class_name = data[domain].get('class_name')  # avoiding KeyError
    elem_id = data[domain].get('id')  # avoiding KeyError

    # temporary solution, cannot soup it directly
    if domain == 'euro-rtv-agd':
        try:
            return float(re.search(r'(?<=price: ")\d{1,4}\.\d{2}', str(soup))[0])
        except TypeError:
            raise AttributeError('Something went wrong there :(')

    attrs = {'class': class_name} if 'class_name' in data[domain] else {'id': elem_id}

    price_text = soup.find(elem_type, attrs=attrs).get_text()
    normalized_text = unicodedata.normalize("NFKD", price_text)
    price_pattern = r'\d{1,3}[\s,.]?\d{1,3}(?:[,.]?\d{2})?'
    price = re.search(price_pattern, normalized_text).group(0)

    if ',' in price and '.' in price:  # to handle coma and dot at the same time, ex: 1,100.00 -> 1100.00
        price = price.replace(',', '')
    else:
        price = price.replace(',', '.')

        price = price.replace(',', '')
    return float(re.sub(r'\s+', '', price))  # removing any eventual whitespaces left


def get_name_from_soup(soup: BeautifulSoup, domain: str) -> str:
    data = {'x-kom': {'elem_type': 'h1', 'class_name': 'sc-1x6crnh-5 cYILyh'},
            'delkom': {'elem_type': 'h1', 'class_name': 'columns twelve'},
            'oleole': {'elem_type': 'h1', 'class_name': 'selenium-KP-product-name'},
            'euro-rtv-agd': {'elem_type': 'h1', 'class_name': 'product-name selenium-KP-product-name'},
            'amazon.com': {'elem_type': 'span', 'id': 'productTitle'}}
    elem_type = data[domain]['elem_type']
    class_name = data[domain].get('class_name')
    elem_id = data[domain].get('id')  # avoiding KeyError

    attrs = {'class': class_name} if 'class_name' in data[domain] else {'id': elem_id}

    plain_text = soup.find(elem_type, attrs=attrs).get_text().strip()
    ascii_text = plain_text.encode('ascii', 'ignore').decode()
    # encoding to ascii and decoding again to get rid of any non-ascii characters

    ascii_text = re.sub(r'["\';]', '', ascii_text)
    # removing ", ' and ; characters for SQL safety - so far didn't find a way to avoid passing
    # table name within f string when creating table, ? placeholders look to be only available for values

    return re.sub(r'\s{2,}', ' ', ascii_text)


def get_content_from_url(url: str) -> bytes:
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
               'x-requested-with': 'XMLHttpRequest'}
    r = requests.get(url, headers=headers)
    return r.content


def get_soup_from_contents(contents: str, parse_type='lxml') -> BeautifulSoup:
    return BeautifulSoup(contents, parse_type)


@timer
def main():
    sqlite = SQLite('prices.db')

    with ThreadPoolExecutor() as executor:
        contents = executor.map(get_content_from_url, rs.urls)
    try:
        laptops = {url: {'name': f'{domain} - {get_name_from_soup(soup, domain)}',
                         'price': get_price_from_soup(soup, domain)}
                   for url, soup, domain in zip(rs.urls, map(get_soup_from_contents, contents),
                                                map(get_domain_from_url, rs.urls))}

    except AttributeError:
        print('Error while souping, sending email')
        email_subject = 'Price tracker crashed on souping one of urls'
        email_body = 'Would you mind taking a look at it?'
        email_handler.send_email(debug_receiver_address, subject=email_subject, body=email_body)
        return -10

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
