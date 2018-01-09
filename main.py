import locale
import os
import re
import traceback
from datetime import datetime
from typing import Optional, Dict, Union, Sequence

import requests
from bs4 import BeautifulSoup

# import click

locale.setlocale(locale.LC_ALL, 'en_US')

BASE_URL = 'https://legacy.bas.ac.uk/webcams/archive/cam.php'
START_URL = '{}?cam=1&position=7'.format(BASE_URL)
ERROR_MSG = 'We are currently only displaying a 30 day archive.'
TIME_RE = re.compile('^[0-9]{2}:[0-9]{2}:[0-9]{2}$')

ParamsType = Dict[str, Union[str, int]]


def parse_datetime(s: str) -> datetime:
    """
    >>> parse_datetime('December 12, 2017 at 23:03')
    datetime.datetime(2017, 12, 12, 23, 3)
    >>> parse_datetime('January 1, 2017 at 08:03')
    datetime.datetime(2017, 1, 1, 8, 3)
    """
    return datetime.strptime(s, '%B %d, %Y at %H:%M')


def adjust_date(dt: datetime, new_time: str) -> datetime:
    hh, mm, ss = new_time.split(':')
    return dt.replace(hour=int(hh), minute=int(mm))


def check_valid(html):
    return ERROR_MSG not in html


def get_html(url: str) -> BeautifulSoup:
    response = requests.get(url)
    response.raise_for_status()
    if check_valid(response.text):
        return BeautifulSoup(response.text, 'html.parser')
    else:
        raise ValueError('Not a valid html page')


def get_image(soup: BeautifulSoup) -> str:
    return soup.find_all(attrs={"class": "webcam_image"})[0].find('img').attrs['src']


def get_time_links(soup: BeautifulSoup) -> Dict[str, str]:
    return {link.text: link.attrs['href'] for link in soup.find_all('a') if TIME_RE.findall(link.text)}


def get_prev_link(soup: BeautifulSoup) -> str:
    return [link.attrs['href'] for link in soup.find_all('a') if link.text == 'Previous Day'][0]


def get_datetime(soup: BeautifulSoup) -> datetime:
    title = soup.find(attrs={'class': 'webcam_image'}).find('h2')
    return parse_datetime(title.text)


def get_next_time(dt: datetime, seen_dates: Sequence[datetime], html: BeautifulSoup) -> Optional[str]:
    for t, link in get_time_links(html).items():
        adjusted_date = adjust_date(dt, t)
        if adjusted_date not in seen_dates:
            return '{}{}'.format(BASE_URL, link)
    return None


def walk(url):
    seen_dates = []
    _url = url
    while True:
        try:
            print('Getting {}'.format(_url))
            html = get_html(_url)
            dt = get_datetime(html)
            seen_dates.append(dt)
            img = get_image(html)
            yield dt, img
            _url = get_next_time(dt, seen_dates, html)
            if _url is None:
                _url = '{}{}'.format(BASE_URL, get_prev_link(html))
        except ValueError:
            print('Done!')
            traceback.print_exc()
            break


def download_image(url: str, fp: str) -> None:
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(fp, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)


def main(output_dir: str = os.path.dirname(__file__)):
    for dt, img in walk(START_URL):
        fp = os.path.join(output_dir, '{}.jpg'.format(dt.isoformat()))
        download_image(img, fp)
        print('{} downloaded'.format(fp))


if __name__ == '__main__':
    main()
