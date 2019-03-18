import os
import pickle
import re
import requests
from typing import Tuple
from bs4 import BeautifulSoup

CATE_HOST = 'https://cate.doc.ic.ac.uk/'


class CateSession:
    def __init__(self, username: str, password: str, use_cache=True):
        self.username = username
        self.password = password
        self.use_cache = use_cache

    @property
    def auth(self) -> Tuple[str, str]:
        return self.username, self.password

    def password_correct(self, password) -> bool:
        resp = requests.head(CATE_HOST, auth=(self.username, password))
        return resp.status_code != requests.codes['unauthorized']

    def load_page(self, url) -> str:
        if self.use_cache and os.path.exists('temp_page.pickle'):
            with open('temp_page.pickle', 'rb') as f:
                response = pickle.load(f)
        else:
            response = requests.get(url, auth=self.auth)
            with open('temp_page.pickle', 'wb') as f:
                pickle.dump(response, f)

        return response.text

    def download(self, url, dest):
        response = requests.get(url, auth=self.auth, allow_redirects=True)
        with open(dest, 'wb') as f:
            f.write(response.content)


class Notes:
    FILE_URL_REGEX = re.compile(r'showfile\.cgi\?(\w|:)')
    COURSE_INFO_REGEX = re.compile(r'(\d+H?):\s+(.+)\s*')
    FILENAME_FORMAT = '{title}.{filetype}'

    def __init__(self, number: int, title: str, filetype: str, url: str,
                 course_id: str, course_name: str):
        self.number = number
        self.title = title
        self.filetype = filetype
        self.url = url
        self.course_id = course_id
        self.course_name = course_name

    def __str__(self):
        return self.format('({number}) {title}.{filetype}')

    @classmethod
    def from_table_row(cls, tr, course_info):
        number, title, filetype, *_ = tr.find_all('td')
        num = int(number.string)
        url = title.find('a')['href']
        return cls(num, title.string, filetype.string, url, *course_info)

    @classmethod
    def get_course_info(cls, soup):
        module_tag = soup.body.find(text=re.compile(r'.*Module.*')).parent
        course_tag = module_tag.find(text=cls.COURSE_INFO_REGEX).parent
        return cls.COURSE_INFO_REGEX.search(course_tag.text).groups()

    @classmethod
    def get_notes_from_url(cls, cate, url):
        page = cate.load_page(url)
        soup = BeautifulSoup(page, 'html.parser')
        dl_links = soup.find_all('a', href=cls.FILE_URL_REGEX)
        trs = [link.parent.parent for link in dl_links]
        course = cls.get_course_info(soup)
        all_notes = [Notes.from_table_row(tr, course) for tr in trs]
        return {notes.number: notes for notes in all_notes}

    def format(self, formatting: str = None) -> str:
        """Formats Notes object according to the given `formatting`

        Args:
            formatting (str, optional): A Python style format string.
                e.g. '{course_id} {course_name} ({number}) {title}.{filetype}'
                formats the string as such: 101 Intro to Python (2) Notes1.pdf

        Returns:
            str: the formatted string
        """
        if formatting is None:
            formatting = self.FILENAME_FORMAT
        return formatting.format(**vars(self))

    def download(self, cate, output_dir=None, format=None) -> str:
        if not output_dir:
            output_dir = '.'
        os.makedirs(output_dir, exist_ok=True)
        filename = self.format(format)
        path = os.path.join(output_dir, filename)
        print('Downloading {} ==> {}'.format(self, path))
        if os.path.exists(path):
            print('Already downloaded')
        else:
            url = CATE_HOST + self.url
            cate.download(url, path)
        return path
