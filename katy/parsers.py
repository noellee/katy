import re
from datetime import timedelta, datetime

from bs4 import Tag

from katy.course import Course
from katy.exercise import Exercise, SubmissionType
import katy.timetable as timetable


class DateRows:
    def __init__(self, table_elem: Tag):
        [
            self.month_row,
            self.week_row,
            self.day_row,
        ] = table_elem.find_all('tr', limit=3)

    def get_month_by_index(self, index: int) -> int:
        month_th = self.month_row.find('th', bgcolor='white')
        colspan = int(month_th.get('colspan', '1'))
        while index >= colspan:
            index -= colspan
            month_th = month_th.find_next_sibling('th')
            colspan = int(month_th.get('colspan', '1'))
        month_str = month_th.get_text(strip=True)
        return datetime.strptime(month_str, '%B').month

    def get_date_by_index(self, index: int, start_year: int, end_year: int) -> datetime:
        initial_index = index

        day_th: Tag = next(self.day_row.children)
        day_th = day_th.find_next_sibling('th')
        while index > 0:
            day_th = day_th.find_next_sibling('th')
            index -= 1
        day_str = day_th.get_text()
        if not day_str:
            offset = 1 if index < 2 else -1
            return self.get_date_by_index(initial_index + offset, start_year, end_year) - timedelta(days=offset)
        day = int(day_str)

        month = self.get_month_by_index(initial_index)

        year = end_year if month <= 7 else start_year

        return datetime(year=year, month=month, day=day)


class TimetableParser:
    def __init__(self, page: Tag):
        self.table_elem = page.select_one('body > p > table')
        self.date_rows = DateRows(self.table_elem)
        self.period, self.start_year, self.end_year = self._parse_title(page)

    @staticmethod
    def _parse_course(course_id_elem: Tag):
        course_id = course_id_elem.get_text()
        course_name = str(course_id_elem.next_sibling).replace(' - ', '')
        return Course(id=course_id, name=course_name)

    @staticmethod
    def _parse_title(page: Tag) -> (str, int, int):
        title = page.find('h1').get_text()
        match = re.search(r'(?P<period>.+)\s+(?P<start>[0-9]+)-(?P<end>[0-9]+)$', title)
        return match.group('period'), int(match.group('start')), int(match.group('end'))

    def _parse_exercise_tr(self, row: Tag, is_first_row: bool) -> [Exercise]:
        skip = 4 if is_first_row else 1
        tds = row.find_all('td')[skip:]

        exercises = []
        index = 0

        for td in tds:
            color = td.get('bgcolor')
            colspan = int(td.get('colspan', '1'))
            submission_type = SubmissionType.from_color(color)

            if submission_type is None:
                index += colspan
                continue

            text = td.get_text(separator=' ', strip=True)
            match = re.match(r'(?P<number>\d+):(?P<type>[A-Z]+)\s*(?P<title>.+)?', text)
            if match is None:
                index += colspan
                continue

            start = self.date_rows.get_date_by_index(index, self.start_year, self.end_year)
            end = start + timedelta(days=colspan - 1)

            exercise = Exercise(
                number=int(match.group('number')),
                title=match.group('title'),
                type=match.group('type'),
                submission_type=submission_type,
                start=start,
                end=end,
            )
            exercises.append(exercise)

            index += colspan

        return exercises

    def _parse_exercises(self, module_rows: [Tag]) -> [Exercise]:
        is_first_row = True
        exercises = []
        for row in module_rows:
            exercises += self._parse_exercise_tr(row, is_first_row)
            is_first_row = False
        return exercises

    @property
    def _course_exercises(self):
        module = next(self.table_elem.children)
        while True:
            course_id = module.find_next('font', color='blue', text=re.compile(r'^[A-Z0-9]+$'))
            if course_id is None:
                break

            module_td = course_id.find_parent('td')
            rowspan = int(module_td['rowspan'])
            module = module_td.parent
            module_rows = []
            for i in range(rowspan):
                module_rows.append(module)
                module = module.next_sibling

            course = self._parse_course(course_id)
            exercises = self._parse_exercises(module_rows)
            yield (course, exercises)

    def parse(self):
        return timetable.Timetable(
            period=self.period,
            start_year=self.start_year,
            end_year=self.end_year,
            _courses=list(self._course_exercises),
        )
