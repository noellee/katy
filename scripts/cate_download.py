#!/usr/bin/env python

import argparse
import getpass
import itertools
import os
import sys
import textwrap
from argparse import RawDescriptionHelpFormatter
from collections import OrderedDict
from typing import Callable, Tuple
from urllib.parse import parse_qs, urlparse
from PyPDF2 import PdfFileMerger

from katy.api import CateSession, Notes


def user_prompt(prompt: str, input_func: Callable[[str], str] = input) -> str:
    try:
        return input_func(prompt)
    except (KeyboardInterrupt, EOFError):
        print()
        print('Exited.')
        sys.exit()


class InteractiveCateSession(CateSession):
    def __init__(self, username: str):
        self.password_is_set = False
        super().__init__(username, '')  # placeholder password

    def request_auth(self):
        prompt = 'Password for [{}]: '.format(self.username)
        password = user_prompt(prompt, getpass.getpass)
        while not self.password_correct(password):
            print('Password incorrect. Try again.')
            password = user_prompt(prompt, getpass.getpass)
        self.password = password
        self.password_is_set = True

    @property
    def auth(self) -> Tuple[str, str]:
        if not self.password_is_set:
            self.request_auth()
        return super().auth


def user_proceed(assume_yes=False):
    if assume_yes:
        return True

    answer = user_prompt('Proceed? [Y/N] ').upper()
    while answer not in {'Y', 'N'}:
        answer = user_prompt('Proceed? [Y/N] ').upper()
    return answer == 'Y'


def main(url, username, notes_range, output_dir, format=None,
         merge_file=None, assume_yes=False):
    cate = InteractiveCateSession(username)
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
        msg = '{} is not a CATe URL'.format(value)
        raise argparse.ArgumentTypeError(msg)

    query = parse_qs(url.query)
    key = query.get('key', None)
    if key is None:
        msg = '{} is not a CATe URL'.format(value)
        raise argparse.ArgumentTypeError(msg)

    return url.geturl()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=textwrap.dedent('''
            Tired of downloading notes from CATe by hand???
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
    parser.add_argument('-y', '--yes', action='store_true',
                        help='automatic yes to prompts')
    parser.add_argument('-f', '--format',
                        help='name format of the downloaded files')
    parser.add_argument('-m', '--merge', dest='merge_file',
                        help='merge the downloaded pdfs into one single pdf')
    args = parser.parse_args()
    username = args.url.split(':')[-1]
    main(args.url, username, args.range, args.output, args.format,
         args.merge_file, args.yes)
