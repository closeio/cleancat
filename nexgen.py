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

def intfield(
    value: Any,
    *,
    nullability: Nullability = Required()
) -> Union[Value[int], Error]:
    # handle nullability
    if value is omitted:
        if isinstance(nullability, Required):
            return Error(field=field, msg='value is required')
        elif isinstance(nullability, Nullable):
            return Value(nullability.null_value)

    # coerce from string if needed
    if isinstance(value, int):
        return Value(value=value)
    elif isinstance(value, str):
        try:
            value = int(value)
        except (ValueError, TypeError):
            return Error(msg='unable to parse int')

    return Error(msg='unhandled type, counld not coerce')



FIELD_TYPE_MAP = {
    int: intfield
}

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

    def run_validators(self, field: Tuple[str, ...], value: Any) -> Union[Value, Error]:
        result = Value(value=value)
        for validator in self.validators:
            result = validator(value=result.value)
            if isinstance(result, Error):
                return wrap_result(field=field, result=result)

        return wrap_result(field=field, result=result)


def field(
    *,
    parents: Tuple[Callable, ...] = tuple(),
    accepts: Tuple[str, ...] = tuple(),
    serialize_to: Optional[str] = None,
):
    def _outer_field(inner_func: Callable):

        field_def = Field(
            validators=parents + (inner_func,),
            accepts=accepts,
            serialize_to=serialize_to
        )

        @functools.wraps(inner_func)
        def _field(field: Tuple[str, ...], value: Any) -> Union[Value, Error]:
            return field_def.run_validators(field, value)

        _field.__field = field_def
        return _field
    return _outer_field

def simple_field(**kwargs):
    def _simple(value):
        return value
    return field(**kwargs)(_simple)

# @schema
# class NestedSchema:
#     anotherstring: str

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

def schema(cls: SchemaCls, getter=getter):
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
            field_def.serialize_to or field_name: getattr(self, field_name)
            for field_name, field_def in get_fields(cls).items()
        }
    cls.__serialize = _serialize


    # TODO some annotations magic

    return cls


def clean(schema: Type[SchemaCls], data) -> SchemaCls:
    return schema.__clean(data)

def serialize(schema: SchemaCls) -> Dict:
    return schema.__serialize()

@schema
class ExampleSchema:
    myint = simple_field(parents=(intfield,), accepts=('myint', 'deprecated_int'))

    @field(parents=(intfield,))
    def mylowint(value: int) -> Union[Value[int], Error]:
        if value < 5:
            return Value(value=value)
        else:
            return Error(msg='Needs to be less than 5')

def test_basic_happy_path():
    test_data = { 'myint': 100, 'mylowint': 2 }
    result = clean(ExampleSchema, test_data)
    assert isinstance(result, ExampleSchema)
    assert result.myint == test_data['myint']
    assert result.mylowint == test_data['mylowint']

    assert test_data == serialize(result)

def test_basic_validation_error():
    test_data = { 'myint': 100, 'mylowint': 10 }
    result = clean(ExampleSchema, test_data)
    assert isinstance(result, ValidationError)
    assert result.errors == [Error(msg='Needs to be less than 5', field=('mylowint',))]

def test_accepts():
    test_data = { 'deprecated_int': 100, 'mylowint': 2 }
    result = clean(ExampleSchema, test_data)
    assert isinstance(result, ExampleSchema)
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
