import pytest
from katy.api import CateSession, Notes


@pytest.fixture
def notes():
    number = 10
    title = 'Notes Example'
    filetype = 'pdf'
    url = 'example.com'
    course_id = '101'
    course_name = 'MyCourse'
    return Notes(number, title, filetype, url, course_id, course_name)


def test_notes_format(notes):
    assert notes.format('{number}') == str(notes.number)
    assert notes.format('{title}') == notes.title
    assert notes.format('{filetype}') == notes.filetype
    assert notes.format('{url}') == notes.url
    assert notes.format('{course_id}') == notes.course_id
    assert notes.format('{course_name}') == notes.course_name
    assert notes.format('example') == 'example'
    with pytest.raises(KeyError):
        assert notes.format(r'{not_exist}') == '{not_exist}'


def test_cate_auth():
    username = 'user'
    password = 'pass'
    cate = CateSession(username, password)
    assert cate.auth == (username, password)
