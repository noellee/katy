#!/usr/bin/env python

import argparse
import getpass
import itertools
import pickle
import re
import requests
import os
import sys
import textwrap
from argparse import RawDescriptionHelpFormatter
from collections import OrderedDict
from typing import Callable, Tuple
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup  # type: ignore
from PyPDF2 import PdfFileMerger

CATE_HOST = 'https://cate.doc.ic.ac.uk/'


def user_prompt(prompt: str, input_func: Callable[[str], str] = input) -> str:
    try:
        return input_func(prompt)
    except (KeyboardInterrupt, EOFError):
        print()
        print('Exited.')
        sys.exit()


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


class CateSession:
    def __init__(self, username: str, use_cache=True):
        self.username = username
        self.password = None
        self.use_cache = use_cache

    @property
    def auth(self) -> Tuple[str, str]:
        if self.password is None:
            self.request_auth()
        return self.username, self.password  # type: ignore

    def password_correct(self, password) -> bool:
        resp = requests.head(CATE_HOST, auth=(self.username, password))
        return resp.status_code != requests.codes['unauthorized']

    def request_auth(self):
        prompt = 'Password for [{}]: '.format(self.username)
        password = user_prompt(prompt, getpass.getpass)
        while not self.password_correct(password):
            print('Password incorrect. Try again.')
            password = user_prompt(prompt, getpass.getpass)
        self.password = password

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


def user_proceed(assume_yes=False):
    if assume_yes:
        return True

    answer = user_prompt('Proceed? [Y/N] ').upper()
    while answer not in {'Y', 'N'}:
        answer = user_prompt('Proceed? [Y/N] ').upper()
    return answer == 'Y'


def main(url, username, notes_range, output_dir, use_cache=True,
         format=None, merge_file=None, assume_yes=False):
    cate = CateSession(username, use_cache)
    notes = Notes.get_notes_from_url(cate, url)
    selected = list(notes_range)
    print('The following marked with a (*) will be downloaded:')
    selected_count = 0
    for num, n in sorted(notes.items()):
        if num in selected:
            prefix = '  * '
            selected_count += 1
        else:
            prefix = '    '
        print(prefix + str(n))

    print('{} out of {} {} selected'.format(
        selected_count,
        len(notes),
        'is' if len(selected) == 1 else 'are',
    ))

    if not user_proceed(assume_yes):
        print('Notes not downloaded.')
        return

    print()
    downloaded = OrderedDict([
        (num, notes[num].download(cate, output_dir, format))
        for num in selected
        if num in notes
    ])

    if merge_file is None:
        return

    print()

    merge_path = os.path.join(output_dir, merge_file)
    print('Downloaded files will be merged to {}'.format(merge_path))

    if not user_proceed(assume_yes):
        print('Downloaded {} notes but not merged.'.format(len(downloaded)))
        return

    merger = PdfFileMerger()
    for n, d in downloaded.items():
        merger.append(d, bookmark=notes[n].title)
    while True:
        try:
            with open(merge_path, 'wb') as f:
                merger.write(f)
                print('Merged!')
            break
        except PermissionError:
            print('Permission error! Is the file open somewhere?')
            user_prompt('Press [Enter] to try again')

    merger.close()


class RangeConverter:
    DEFAULT_SEPARATOR = '-'

    def __init__(self, separator=DEFAULT_SEPARATOR):
        self.separator = separator

    def __call__(self, value):
        ranges = value.split(self.separator, 1)

        if any(not r.isdigit() for r in ranges):
            msg = '{} is not a valid range'.format(value)
            raise argparse.ArgumentTypeError(msg)

        ranges = list(map(int, ranges))
        start = ranges[0]
        end = ranges[1] if len(ranges) > 1 else start
        return range(start, end + 1)


class ChainRanges(argparse.Action):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, itertools.chain(*values))


def is_cate_url(value):
    url = urlparse(value)
    if not url.netloc == 'cate.doc.ic.ac.uk':
        msg = '{} is not a CaTE URL'.format(value)
        raise argparse.ArgumentTypeError(msg)

    query = parse_qs(url.query)
    key = query.get('key', None)
    if key is None:
        msg = '{} is not a CaTE URL'.format(value)
        raise argparse.ArgumentTypeError(msg)

    return url.geturl()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=textwrap.dedent('''
            Tired of downloading notes from CaTE by hand???
            This is what you need. Just copy the URL of your notes page!

            To download one single notes file (e.g. numbered 10), run:
            $ ./cate_download.py [long cate url] 10

            To download multiple notes (e.g. numbered from 1 to 10), run:
            $ ./cate_download.py [long cate url] 1-10

            Ranges can be combined, as such:
            $ ./cate_download.py [long cate url] 1-10 2-19 100

            TOO MANY FILES??? Merge them!
            $ ./cate_download.py [long cate url] 7 2-4 --merge allnotes.pdf
            Merging respects the order specified in the arguments! In this
            example, the resulting order in the merged file is 7,2,3,4.
        '''),
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument('url', type=is_cate_url,
                        help='''URL to the notes page''')
    parser.add_argument('range',
                        type=RangeConverter(),
                        action=ChainRanges,
                        nargs='*',
                        help='''
                            Range of notes to download.
                            In the following formats: 1-10 or 12
                        ''')
    parser.add_argument('-o', '--output',
                        help='folder to save the downloaded and merged files')
    parser.add_argument('--no-cache', dest='use_cache', action='store_false',
                        help='do not use cached pages')
    parser.add_argument('-y', '--yes', action='store_true',
                        help='automatic yes to prompts')
    parser.add_argument('-f', '--format',
                        help='name format of the downloaded files')
    parser.add_argument('-m', '--merge', dest='merge_file',
                        help='merge the downloaded pdfs into one single pdf')
    args = parser.parse_args()
    username = args.url.split(':')[-1]
    main(args.url, username, args.range, args.output, args.use_cache,
         args.format, args.merge_file, args.yes)
