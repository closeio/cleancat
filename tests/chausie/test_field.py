import enum
from typing import Union, Optional, List, Set

import attr
import pytest

from cleancat.chausie.consts import omitted
from cleancat.chausie.field import (
    intfield,
    Error,
    field,
    ValidationError,
    Optional as CCOptional,
    strfield,
    listfield,
    nestedfield,
    enumfield,
)
from cleancat.chausie.schema import schema, clean, serialize


@pytest.fixture
def example_schema():
    @schema
    class ExampleSchema:
        myint = field(intfield, accepts=('myint', 'deprecated_int'))

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
        myint = field(intfield, serialize_to='my_new_int')

    result = clean(MySchema, {'myint': 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert serialize(result) == {'my_new_int': 100}


def test_serialize_func():
    def double(value):
        return value * 2

    @schema
    class MySchema:
        myint = field(intfield, serialize_func=double)

    result = clean(MySchema, {'myint': 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert serialize(result) == {'myint': 200}


def test_intfield():
    @schema
    class MySchema:
        val: int = field(intfield)

    result = clean(MySchema, {'val': 5})
    assert isinstance(result, MySchema)
    assert result.val == 5


def test_strfield():
    @schema
    class UserSchema:
        name: str

    result = clean(UserSchema, {'name': 'John'})
    assert isinstance(result, UserSchema)
    assert result.name == 'John'


class TestListField:
    def test_listfield_basic(self):
        @schema
        class UserSchema:
            aliases = field(listfield(field(strfield)))

        result = clean(UserSchema, {'aliases': ['John', 'Johnny']})
        assert isinstance(result, UserSchema)
        assert result.aliases == ['John', 'Johnny']

    def test_listfield_empty(self):
        @schema
        class UserSchema:
            aliases = field(listfield(field(strfield)))

        result = clean(UserSchema, {'aliases': ['John', 'Johnny']})
        assert isinstance(result, UserSchema)
        assert result.aliases == ['John', 'Johnny']

    def test_listfield_inner_optional(self):
        @schema
        class UserSchema:
            aliases = field(
                listfield(field(strfield, nullability=CCOptional()))
            )

        result = clean(UserSchema, {'aliases': ['John', None]})
        assert isinstance(result, UserSchema)
        assert result.aliases == ['John', None]

    def test_listfield_chained(self):
        @attr.frozen
        class Alias:
            value: str

        @schema
        class UserSchema:
            @field(parents=(listfield(field(strfield)),))
            def aliases(value: List[str]) -> List[Alias]:
                return [Alias(v) for v in value]

        result = clean(UserSchema, {'aliases': ['John', 'Johnny']})
        assert isinstance(result, UserSchema)
        assert result.aliases == [Alias(value='John'), Alias(value='Johnny')]

    def test_listfield_parent_context(self):
        @attr.frozen
        class Context:
            valid_suffixes: Set[str]

        def validate_suffix(value: str, context: Context):
            if value not in context.valid_suffixes:
                return Error(msg='Suffix is invalid')
            return value

        @schema
        class UserSchema:
            suffixes = field(
                listfield(field(validate_suffix, parents=(strfield,)))
            )

        context_ = Context(valid_suffixes={'Sr', 'Jr', '2nd'})
        result = clean(
            UserSchema, {'suffixes': ['Sr', 'Jr']}, context=context_
        )
        assert isinstance(result, UserSchema)
        assert result.suffixes == ['Sr', 'Jr']

    def test_listfield_context(self):
        @attr.frozen
        class Context:
            valid_suffixes: Set[str]

        @schema
        class UserSchema:
            @field(parents=(listfield(field(strfield)),))
            def suffixes(
                value: List[str], context: Context
            ) -> Union[List[str], Error]:
                for suffix in value:
                    if suffix not in context.valid_suffixes:
                        return Error(msg='Suffix is invalid')
                return value

        context_ = Context(valid_suffixes={'Sr', 'Jr', '2nd'})
        result = clean(
            UserSchema, {'suffixes': ['Sr', 'Jr']}, context=context_
        )
        assert isinstance(result, UserSchema)
        assert result.suffixes == ['Sr', 'Jr']


class TestNullability:
    def test_required_omitted(self):
        @schema
        class MySchema:
            myint: int

        result = clean(MySchema, {})
        assert isinstance(result, ValidationError)
        assert result.errors == [
            Error(msg='Value is required.', field=('myint',))
        ]

    def test_required_none(self):
        @schema
        class MySchema:
            myint: int

        result = clean(MySchema, {'myint': None})
        assert isinstance(result, ValidationError)
        assert result.errors == [
            Error(
                msg='Value is required, and must not be None.',
                field=('myint',),
            )
        ]

    def test_optional_omitted(self):
        @schema
        class MySchema:
            myint: Optional[int]

        result = clean(MySchema, {})
        assert isinstance(result, MySchema)
        assert result.myint is omitted

    def test_optional_none(self):
        @schema
        class MySchema:
            myint: Optional[int]

        result = clean(MySchema, {'myint': None})
        assert isinstance(result, MySchema)
        assert result.myint is None


class TestNestedField:
    def test_nestedfield_basic(self):
        @schema
        class InnerSchema:
            a: str

        @schema
        class OuterSchema:
            inner = field(nestedfield(InnerSchema))

        result = clean(OuterSchema, {'inner': {'a': 'John'}})
        assert isinstance(result, OuterSchema)
        assert isinstance(result.inner, InnerSchema)
        assert result.inner.a == 'John'

    def test_nestedfield_with_context(self):
        @attr.frozen
        class Context:
            curr_user_id: str

        @schema
        class InnerSchema:
            @field(parents=(strfield,))
            def a(value: str, context: Context) -> str:
                return f'{value}:{context.curr_user_id}'

        @schema
        class OuterSchema:
            inner = field(nestedfield(InnerSchema))

        result = clean(
            OuterSchema,
            {'inner': {'a': 'John'}},
            context=Context(curr_user_id='user_abc'),
        )
        assert isinstance(result, OuterSchema)
        assert isinstance(result.inner, InnerSchema)
        assert result.inner.a == 'John:user_abc'


class TestEnumField:
    def test_enumfield_basic(self):
        class Color(enum.Enum):
            BLUE = 'blue'
            RED = 'red'
            GREEN = 'green'

        @schema
        class MySchema:
            color = field(enumfield(Color))

        result = clean(MySchema, {'color': 'blue'})
        assert isinstance(result, MySchema)
        assert isinstance(result.color, Color)
        assert result.color is Color.BLUE

    @pytest.mark.parametrize('bad_value', ['black', 5, object()])
    def test_enumfield_error(self, bad_value):
        class Color(enum.Enum):
            BLUE = 'blue'
            RED = 'red'
            GREEN = 'green'

        @schema
        class MySchema:
            color = field(enumfield(Color))

        result = clean(MySchema, {'color': bad_value})
        assert isinstance(result, ValidationError)
        assert result.errors == [
            Error(msg='Invalid value for enum.', field=('color',))
        ]


def test_field_self():
    @schema
    class AliasSchema:
        @field(parents=(strfield,))
        def value(self, value: str):
            return f'Value:{value}'

    result = clean(AliasSchema, {'value': 'John'})
    assert isinstance(result, AliasSchema)
    assert result.value == 'Value:John'


def test_extendable_fields():
    # we should be able to define reusable/composable fields with their own parents
    # TODO should this be a different function that makes it clearer this only applies parents as validators?
    @field(parents=(strfield,))
    def valuefield(value: str):
        return f'Value:{value}'

    @schema
    class MySchema:
        @field(parents=(valuefield,))
        def a(self, value: str):
            return f'a:{value}'

    result = clean(MySchema, {'a': 'John'})
    assert isinstance(result, MySchema)
    assert result.a == 'a:Value:John'
