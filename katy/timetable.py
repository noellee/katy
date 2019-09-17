from dataclasses import dataclass, field

from bs4 import BeautifulSoup

import katy.parsers as parsers
from katy.api import CateSession
from katy.course import Course
from katy.exercise import Exercise


@dataclass
class Timetable:
    period: str
    start_year: int
    end_year: int
    _courses: [(Course, [Exercise])] = field(repr=False)

    def __getitem__(self, key: Course) -> [Exercise]:
        for (course, exercises) in self._courses:
            if course == key:
                return exercises
        raise KeyError(str(key))

    @property
    def courses(self):
        return [course for (course, _) in self._courses]

    @staticmethod
    def get_timetable_from_url(cate: CateSession, url: str):
        page = cate.load_page(url)
        soup = BeautifulSoup(page, 'html.parser')
        parser = parsers.TimetableParser(soup)
        return parser.parse()
