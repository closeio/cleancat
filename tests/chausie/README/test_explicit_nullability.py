from typing import Optional, Union
from cleancat.chausie.consts import OMITTED, omitted
from cleancat.chausie.field import (
    field,
    strfield,
    Optional as CCOptional,
    Required,
)
from cleancat.chausie.schema import Schema
import pytest


class NullabilityExample(Schema):
    # auto defined based on annotations
    nonnull_required: str
    nullable_omittable: Optional[str]

    # manually specified
    nonnull_omittable: Union[str, OMITTED] = field(
        strfield, nullability=CCOptional(allow_none=False)
    )
    nullable_required: Optional[str] = field(
        strfield, nullability=Required(allow_none=True)
    )


@pytest.mark.parametrize(
    'payload,expected_result',
    [
        (
            {},
            {
                'errors': [
                    {
                        'msg': 'Value is required.',
                        'field': ('nonnull_required',),
                    },
                    {
                        'msg': 'Value is required.',
                        'field': ('nullable_required',),
                    },
                ]
            },
        ),
        (
            {'nonnull_required': None, 'nullable_required': None},
            {
                'errors': [
                    {
                        'msg': 'Value is required, and must not be None.',
                        'field': ('nonnull_required',),
                    }
                ]
            },
        ),
        (
            {'nonnull_required': 'test', 'nullable_required': None},
            {
                'nullable_required': None,
                'nonnull_required': 'test',
            },
        ),
        (
            {
                'nonnull_required': 'test',
                'nullable_required': None,
                'nonnull_omittable': None,
            },
            {
                'errors': [
                    {
                        'msg': 'Value must not be None.',
                        'field': ('nonnull_omittable',),
                    }
                ]
            },
        ),
        (
            {
                'nonnull_required': 'test',
                'nullable_required': None,
                'nonnull_omittable': 'another test',
            },
            {
                'nonnull_omittable': 'another test',
                'nullable_required': None,
                'nonnull_required': 'test',
            },
        ),
        (
            {
                'nonnull_required': 'test',
                'nullable_required': None,
                'nonnull_omittable': 'another test',
                'nullable_omittable': None,
            },
            {
                'nonnull_required': 'test',
                'nullable_required': None,
                'nonnull_omittable': 'another test',
                'nullable_omittable': None,
            },
        ),
    ],
)
def test_nullability_example(payload, expected_result):
    actual_result = NullabilityExample.clean(payload).serialize()
    assert actual_result == expected_result
