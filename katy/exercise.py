from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SubmissionType(Enum):
    UNASSESSED = 1
    UNASSESSED_SUBMISSION_REQUIRED = 2
    ASSESSED_INDIVIDUAL = 3
    ASSESSED_GROUP = 4

    @staticmethod
    def from_color(color: str):
        return {
            'white': SubmissionType.UNASSESSED,
            '#cdcdcd': SubmissionType.UNASSESSED_SUBMISSION_REQUIRED,
            '#ccffcc': SubmissionType.ASSESSED_INDIVIDUAL,
            '#f0ccf0': SubmissionType.ASSESSED_GROUP,
        }.get(color)


@dataclass
class Exercise:
    number: int
    title: str
    type: str
    submission_type: SubmissionType
    start: datetime
    end: datetime
