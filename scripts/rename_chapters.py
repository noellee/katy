#! /usr/bin/env python3

import argparse
from PyPDF2 import PdfFileReader, PdfFileWriter


def main(pdf_file, new_chapters_file, output_file):
    with open(new_chapters_file) as f:
        new_chapters = [line.strip() for line in f.readlines()]

    reader = PdfFileReader(pdf_file)
    writer = PdfFileWriter()

    old_chapters = {
        chapter['/Page']: chapter['/Title']
        for chapter in reader.outlines
    }

    if len(old_chapters) != len(new_chapters):
        print('Number of chapters unequal')
        return

    chapter_pairs = zip(sorted(old_chapters.items()), new_chapters)
    for (page_num, old_chapter), new_chapter in chapter_pairs:
        print('[p.{}] {} => {}'.format(page_num, old_chapter, new_chapter))

    for i in range(reader.getNumPages()):
        page = reader.getPage(i)
        writer.addPage(page)

    chapter_pairs = zip(sorted(old_chapters), new_chapters)
    for page_num, new_chapter in chapter_pairs:
        writer.addBookmark(new_chapter, page_num)

    with open(output_file, 'wb') as f:
        writer.write(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''
        Rename chapters based on an input file
    ''')
    parser.add_argument('pdf', help='PDF file containing the old chapters')
    parser.add_argument('chapters',
                        help='''
                            Plain text file to read the updated chapters from.
                            One line represents one chapter.
                        ''')
    parser.add_argument('output', help='Output file')
    args = parser.parse_args()
    main(args.pdf, args.chapters, args.output)
