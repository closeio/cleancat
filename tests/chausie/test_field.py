from typing import Union

import pytest

from cleancat.chausie.field import simple_field, intfield, Error, field, ValidationError
from cleancat.chausie.schema import schema, clean, serialize


@pytest.fixture
def example_schema():
    @schema
    class ExampleSchema:
        myint = simple_field(
            parents=(intfield,), accepts=('myint', 'deprecated_int')
        )

        @field(parents=(intfield,))
        def mylowint(value: int) -> Union[int, Error]:
            if value < 5:
                return value
            else:
                return Error(msg='Needs to be less than 5')

    return ExampleSchema


def test_basic_happy_path(example_schema):
    test_data = {'myint': 100, 'mylowint': 2}
    result = clean(example_schema, test_data)
    assert isinstance(result, example_schema)
    assert result.myint == test_data['myint']
    assert result.mylowint == test_data['mylowint']

    assert test_data == serialize(result)


def test_basic_validation_error(example_schema):
    test_data = {'myint': 100, 'mylowint': 10}
    result = clean(example_schema, test_data)
    assert isinstance(result, ValidationError)
    assert result.errors == [
        Error(msg='Needs to be less than 5', field=('mylowint',))
    ]


def test_accepts(example_schema):
    test_data = {'deprecated_int': 100, 'mylowint': 2}
    result = clean(example_schema, test_data)
    assert isinstance(result, example_schema)
    assert result.myint == test_data['deprecated_int']

    assert serialize(result) == {
        'myint': test_data['deprecated_int'],
        'mylowint': 2,
    }


def test_serialize_to():
    @schema
    class MySchema:
        myint = simple_field(
            parents=(intfield,),
            serialize_to='my_new_int',
        )

    result = clean(MySchema, {'myint': 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert serialize(result) == {'my_new_int': 100}


def test_serialize_func():
    def double(value):
        return value * 2

    @schema
    class MySchema:
        myint = simple_field(
            parents=(intfield,),
            serialize_func=double,
        )

    result = clean(MySchema, {'myint': 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert serialize(result) == {'myint': 200}

def test_required():
    @schema
    class MySchema:
        myint: int

    result = clean(MySchema, {})
    assert isinstance(result, ValidationError)
    assert result.errors == [Error(msg='Value is required.', field=('myint',))]

def test_strfield():
    @schema
    class UserSchema:
        name: str

    result = clean(UserSchema, {'name': 'John'})
    assert isinstance(result, UserSchema)
    assert result.name == 'John'

