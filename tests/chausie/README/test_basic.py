from typing import Dict, List
from cleancat.chausie.field import (
    field,
    emailfield,
    listfield,
    urlfield,
    ValidationError,
)
from cleancat.chausie.schema import Schema
import pytest

# flask is not tested
# from flask import app, request, jsonify


class JobApplication(Schema):
    first_name: str
    last_name: str
    email: str = field(emailfield())
    urls: List[str] = field(listfield(urlfield(default_scheme='http://')))


# again, not testing against flask
# @app.route('/job_application', methods=['POST'])
def my_view(request_json) -> Dict:
    result = JobApplication.clean(request_json)
    if isinstance(result, ValidationError):
        return {
            'errors': [{'msg': e.msg, 'field': e.field} for e in result.errors]
        }

    # Now "result" has the validated data, in the form of a `JobApplication` instance.
    assert isinstance(result, JobApplication)
    name = f'{result.first_name} {result.last_name}'
    return {'name': name, 'contact': result.email, 'hmu': result.urls}


@pytest.mark.parametrize(
    'payload,expected_result',
    [
        (
            {},
            {
                'errors': [
                    {'msg': 'Value is required.', 'field': ('last_name',)},
                    {'msg': 'Value is required.', 'field': ('first_name',)},
                    {'msg': 'Value is required.', 'field': ('urls',)},
                    {'msg': 'Value is required.', 'field': ('email',)},
                ]
            },
        ),
        (
            {
                'first_name': None,
                'last_name': None,
                'urls': None,
                'email': None,
            },
            {
                'errors': [
                    {
                        'msg': 'Value is required, and must not be None.',
                        'field': ('last_name',),
                    },
                    {
                        'msg': 'Value is required, and must not be None.',
                        'field': ('first_name',),
                    },
                    {
                        'msg': 'Value is required, and must not be None.',
                        'field': ('urls',),
                    },
                    {
                        'msg': 'Value is required, and must not be None.',
                        'field': ('email',),
                    },
                ]
            },
        ),
        (
            {
                'first_name': '',  # empty strings are valid by default
                'last_name': '',
                'urls': ['spam'],  # but that's not a real url
                'email': 'john',  # and that's not a real email
            },
            {
                'errors': [
                    {'msg': 'Invalid input.', 'field': ('urls', 0)},
                    {'msg': 'Invalid input.', 'field': ('email',)},
                ]
            },
        ),
        (
            {
                'first_name': 'John',
                'last_name': 'Gibbons',
                'urls': ['johngibbons.com'],
                'email': 'john@johnGibbons.com',
            },
            {
                'name': 'John Gibbons',
                'contact': 'john@johnGibbons.com',
                'hmu': ['http://johngibbons.com'],
            },
        ),
    ],
)
def test_my_view(payload, expected_result):
    actual_result = my_view(payload)
    assert actual_result == expected_result
