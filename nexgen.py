import pytest
import attr
from typing import Generic, TypeVar, Type, Union, Dict, List, Tuple, Any, Callable, Optional
import functools

@attr.frozen
class ValidationError:
    errors: List['Error']

@attr.frozen
class Error:
    msg: str
    field: Tuple[str, ...] = tuple()

class OMITTED:
    """used as singleton for omitted values in validation"""

omitted = OMITTED()

class EMPTY:
    """used as singleton for omitted options/kwargs"""

empty = EMPTY()

T = TypeVar('T')

@attr.frozen
class Value(Generic[T]):
    value: Union[T, OMITTED]  # not sure how to express this

class Nullability:
    pass

class Required(Nullability):
    pass

@attr.frozen
class Nullable(Nullability):
    null_value: Any = omitted

def intfield(value: Any) -> Union[Value[int], Error]:
    # coerce from string if needed
    if isinstance(value, int):
        return Value(value=value)
    elif isinstance(value, str):
        try:
            value = int(value)
        except (ValueError, TypeError):
            return Error(msg='Unable to parse int from given string.')

    return Error(msg='Unhandled type, could not coerce.')

def strfield(value: Any) -> Union[Value[str], Error]:
    if isinstance(value, str):
        return Value(value=value)

    return Error(msg='Unhandled type')



ValueOrError = TypeVar('ValueOrError', bound=Union[Value, Error])

def wrap_result(field: Tuple[str, ...], result) -> ValueOrError:
    if isinstance(result, Error):
        return attr.evolve(result, field=field + result.field)
    elif not isinstance(result, Value):
        return Value(value=result)
    return result


@attr.frozen
class Field:
    validators: Tuple[Callable, ...]
    """Callable that validate a the given field's value."""

    accepts: Tuple[str]
    """Field names accepted when parsing unvalidated input.

    If left unspecified, effectively defaults to the name of the attribute
    defined on the schema.
    """

    serialize_to: Optional[str]
    """If provided overrides the name of the field during seiralialization."""

    serialize_func: Optional[Callable]
    """If provided, will be used when serializing this field."""

    nullability: Nullability

    def run_validators(self, field: Tuple[str, ...], value: Any) -> Union[Value, Error]:
        # handle nullability
        if value is omitted:
            if isinstance(self.nullability, Required):
                return wrap_result(
                    field=field,
                    result=Error(msg='Value is required.')
                )
            elif isinstance(self.nullability, Nullable):
                return Value(self.nullability.null_value)

        result = Value(value=value)
        for validator in self.validators:
            result = validator(value=result.value)
            if isinstance(result, Error):
                return wrap_result(field=field, result=result)

        return wrap_result(field=field, result=result)

def noop(value):
    return value

def field(
    *,
    parents: Tuple[Callable, ...] = tuple(),
    accepts: Tuple[str, ...] = tuple(),
    serialize_to: Optional[str] = None,
    serialize_func: Callable = noop,
    nullability: Nullability = Required(),
):
    def _outer_field(inner_func: Callable):

        field_def = Field(
            nullability=nullability,
            validators=parents + (inner_func,),
            accepts=accepts,
            serialize_to=serialize_to,
            serialize_func=serialize_func,
        )

        @functools.wraps(inner_func)
        def _field(field: Tuple[str, ...], value: Any) -> Union[Value, Error]:
            return field_def.run_validators(field, value)

        _field.__field = field_def
        return _field
    return _outer_field

def simple_field(**kwargs):
    """Passthrough to make defining simple fields cleaner."""
    def _simple(value):
        return value
    return field(**kwargs)(_simple)

def getter(dict_or_obj, field, default):
    if isinstance(dict_or_obj, dict):
        return dict_or_obj.get(field, omitted)
    else:
        getattr(dict_or_obj, field, omitted)

SchemaCls = TypeVar('SchemaCls')

def get_fields(cls: SchemaCls) -> Dict[str, Callable]:
    return {
            field_name: value.__field
        for field_name, value in cls.__dict__.items()
        if (
            callable(value)
            and isinstance(getattr(value, '__field', None), Field)
        )
    }

FIELD_TYPE_MAP = {
    int: intfield,
    str: strfield,
}

def schema(cls: SchemaCls, getter=getter, autodef=True):
    """
    Annotate a class to turn it into a schema.

    Args:
        getter: given an object + field name, gets the value from the obj
        autodef: automatically define simple fields for annotated attributes
    """
    # auto define simple annotations
    if autodef:
        existing_fields = get_fields(cls)
        for field, f_type in getattr(cls, '__annotations__', {}).items():
            if field not in existing_fields:
                setattr(
                    cls,
                    field,
                    simple_field(parents=(FIELD_TYPE_MAP[f_type],)),
                )

    def _clean(data: Any) -> Union[SchemaCls, ValidationError]:
        # how to iterate over all methods?
        results: Dict[str, Union[Value, Error]] = {}
        for field_name, field_def in get_fields(cls).items():
            accepts = field_def.accepts or (field_name,)
            for accept in accepts:
                value = getter(data, accept, omitted)
                if value is not omitted:
                    break

            results[field_name] = field_def.run_validators(
                field=(field_name,), value=value
            )

        errors = {
            f: v for f, v in results.items() if isinstance(v, Error)
        }
        if errors:
            return ValidationError(errors=list(errors.values()))

        return cls(**results)
    cls.__clean = _clean

    def _new_init(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v.value)
    cls.__init__ = _new_init

    def _serialize(self):
        # very simple serialize
        return {
            field_def.serialize_to or field_name: (
                field_def.serialize_func(getattr(self, field_name))
            )
            for field_name, field_def in get_fields(cls).items()
        }
    cls.__serialize = _serialize

    return cls


def clean(schema: Type[SchemaCls], data) -> SchemaCls:
    return schema.__clean(data)

def serialize(schema: SchemaCls) -> Dict:
    return schema.__serialize()

@pytest.fixture
def example_schema():
    @schema
    class ExampleSchema:
        myint = simple_field(parents=(intfield,), accepts=('myint', 'deprecated_int'))

        @field(parents=(intfield,))
        def mylowint(value: int) -> Union[Value[int], Error]:
            if value < 5:
                return Value(value=value)
            else:
                return Error(msg='Needs to be less than 5')
    return ExampleSchema

def test_basic_happy_path(example_schema):
    test_data = { 'myint': 100, 'mylowint': 2 }
    result = clean(example_schema, test_data)
    assert isinstance(result, example_schema)
    assert result.myint == test_data['myint']
    assert result.mylowint == test_data['mylowint']

    assert test_data == serialize(result)

def test_basic_validation_error(example_schema):
    test_data = { 'myint': 100, 'mylowint': 10 }
    result = clean(example_schema, test_data)
    assert isinstance(result, ValidationError)
    assert result.errors == [Error(msg='Needs to be less than 5', field=('mylowint',))]

def test_accepts(example_schema):
    test_data = { 'deprecated_int': 100, 'mylowint': 2 }
    result = clean(example_schema, test_data)
    assert isinstance(result, example_schema)
    assert result.myint == test_data['deprecated_int']

    assert (
        serialize(result) == {'myint': test_data['deprecated_int'], 'mylowint': 2}
    )

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
            parents=(intfield,), serialize_func=double,
        )

    result = clean(MySchema, {'myint': 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert serialize(result) == {'myint': 200}

def test_autodef():
    @schema
    class MySchema:
        myint: int

    result = clean(MySchema, {'myint': 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert serialize(result) == {'myint': 100}

def test_required():
    @schema
    class MySchema:
        myint: int

    result = clean(MySchema, {})
    assert isinstance(result, ValidationError)
    assert result.errors == [Error(msg='Value is required.', field=('myint',))]

def test_nullable():
    @schema
    class MySchema:
        myint: Optional[int] = simple_field(
            parents=(intfield,), nullability=Nullable(null_value=None)
        )

    result = clean(MySchema, {})
    assert isinstance(result, MySchema)
    assert result.myint == None

def test_strfield():
    @schema
    class UserSchema:
        name: str

    result = clean(UserSchema, {'name': 'John'})
    assert isinstance(result, UserSchema)
    assert result.name == 'John'


