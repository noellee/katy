from dataclasses import dataclass, field
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from icalendar import Calendar, Event

import katy.parsers as parsers
from katy.api import CateSession
from katy.course import Course
from katy.exercise import Exercise, SubmissionType


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

    def to_ical(self) -> Calendar:
        now = datetime.utcnow()
        cal = Calendar()
        cal.add('prodid', 'Timetable')
        cal.add('version', '1.0')

        level_3_courses = filter(lambda c: c[0].level == 3, self._courses)
        for (course, exercises) in level_3_courses:
            submissions = filter(lambda e: e.submission_type != SubmissionType.UNASSESSED, exercises)
            for exercise in submissions:
                event = Event()
                event.add('summary', f'({exercise.type}) {course.id} {course.name}: {exercise.title}')
                event.add('dtstart', exercise.end)
                event.add('dtend', exercise.end + timedelta(days=1))
                event.add('dtstamp', now)
                cal.add_component(event)
        return cal

    def to_ical_str(self) -> str:
        return str(self.to_ical().to_ical(), 'utf-8')
