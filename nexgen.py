import pytest
import attr
from typing import Generic, TypeVar, Type, Union, Dict, List, Tuple, Any, Callable
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
    field: Tuple[str, ...],
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


def field(*, parents: Tuple[Callable, ...] =tuple()):
    def _outer_field(inner_func: Callable):
        @functools.wraps(inner_func)
        def _field(field: Tuple[str, ...], value: Any) -> Union[Value, Error]:
            result = Value(value=value)
            for parent in parents:
                result = parent(field=field, value=result.value)
                if isinstance(result, Error):
                    return wrap_result(field=field, result=result)

            return wrap_result(field=field, result=inner_func(result.value))

        _field.__field = True
        return _field
    return _outer_field

def simple_field(parents: Tuple[Callable]):
    def _simple(value):
        return value
    return field(parents=parents)(_simple)

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
            field_name: field_validator
        for field_name, field_validator in cls.__dict__.items()
        if (
            callable(field_validator)
            and getattr(field_validator, '__field', None)
        )
    }

def schema(cls: SchemaCls, getter=getter):
    def _clean(data: Any) -> Union[SchemaCls, ValidationError]:
        # how to iterate over all methods?
        results: Dict[str, Union[Value, Error]] = {}
        for field_name, field_validator in get_fields(cls).items():
            results[field_name] = field_validator(
                field=(field_name,),
                value=getter(data, field_name, omitted)
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
            field_name: getattr(self, field_name)
            for field_name in get_fields(cls).keys()
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
    myint = simple_field(parents=(intfield,))
    # @field(parents=(intfield,))
    # def myint(value: int) -> int:
    #     return value

    @field(parents=(intfield,))
    def mylowint(value: int) -> Union[Value[int], Error]:
        if value < 5:
            return Value(value=value)
        else:
            return Error(msg='Needs to be less than 5')

def test_basic_happy_path():
    # passes
    test_data = { 'myint': 100, 'mylowint': 2 }
    result = clean(ExampleSchema, test_data)
    assert isinstance(result, ExampleSchema)
    assert result.myint == test_data['myint']
    assert result.mylowint == test_data['mylowint']

    assert test_data == serialize(result)

def test_basic_validation_error():
    # passes
    test_data = { 'myint': 100, 'mylowint': 10 }
    result = clean(ExampleSchema, test_data)
    assert isinstance(result, ValidationError)
    assert result.errors == [Error(msg='Needs to be less than 5', field=('mylowint',))]

