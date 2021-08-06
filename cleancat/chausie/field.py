import functools
import inspect

import attr
from typing import (
    Generic,
    TypeVar,
    Union,
    Dict,
    List,
    Tuple,
    Any,
    Callable,
    Optional as T_Optional,
)

from cleancat.chausie.consts import OMITTED, omitted, empty


@attr.frozen
class ValidationError:
    errors: List['Error']


@attr.frozen
class Error:
    msg: str
    field: Tuple[str, ...] = tuple()


T = TypeVar('T')


@attr.frozen
class Value(Generic[T]):
    value: Union[T, OMITTED]  # not sure how to express this


class Nullability:
    pass


class Required(Nullability):
    pass


@attr.frozen
class Optional(Nullability):
    omitted_value: Any = omitted


ValueOrError = TypeVar('ValueOrError', bound=Union[Value, Error])


def wrap_result(field: Tuple[str, ...], result: Any) -> ValueOrError:
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

    serialize_to: T_Optional[str]
    """If provided overrides the name of the field during seiralialization."""

    serialize_func: T_Optional[Callable]
    """If provided, will be used when serializing this field."""

    nullability: Nullability

    depends_on: Tuple[str, ...]
    """Other fields on the same schema this field depends on"""

    def run_validators(
            self,
            field: Tuple[str, ...],
            value: Any,
            context: Any,
            intermediate_results: Dict[str, Any],
    ) -> Union[Value, Error]:
        def _get_deps(func):
            return {
                param for param in inspect.signature(func).parameters.keys()
            }

        # handle nullability
        if value is omitted and any(
                ['value' in _get_deps(v) for v in self.validators]
        ):
            if isinstance(self.nullability, Required):
                return wrap_result(
                    field=field, result=Error(msg='Value is required.')
                )
            elif isinstance(self.nullability, Optional):
                return Value(self.nullability.omitted_value)
            else:
                raise TypeError

        def inject_deps(func, val):
            deps = _get_deps(func)
            if not deps:
                return func

            if 'context' in deps and context is empty:
                raise ValueError(
                    'Context is required for evaluating this schema.'
                )

            return functools.partial(
                func,
                **{
                    dep: v.value
                    for dep, v in intermediate_results.items()
                    if dep in deps
                },
                **{
                    dep: v
                    for dep, v in {'context': context, 'value': val}.items()
                    if dep in deps
                },
            )

        result = value
        for validator in self.validators:
            result = inject_deps(func=validator, val=result)()
            if isinstance(result, Error):
                return wrap_result(field=field, result=result)

        return wrap_result(field=field, result=result)


def noop(value):
    return value


def field(
        *,
        parents: Tuple[Callable, ...] = tuple(),
        accepts: Tuple[str, ...] = tuple(),
        serialize_to: T_Optional[str] = None,
        serialize_func: Callable = noop,
        nullability: Nullability = Required(),
):
    def _outer_field(inner_func: Callable):
        # find any declared dependencies on other fields
        deps = tuple(
            n
            for n in inspect.signature(inner_func).parameters.keys()
            if n not in {'context', 'value'}
        )

        return Field(
            nullability=nullability,
            validators=parents + (inner_func,),
            accepts=accepts,
            serialize_to=serialize_to,
            serialize_func=serialize_func,
            depends_on=deps,
        )

    return _outer_field


def simple_field(**kwargs):
    """Passthrough to make defining simple fields cleaner."""

    def _simple(value):
        return value

    return field(**kwargs)(_simple)


def intfield(value: Any) -> Union[int, Error]:
    # coerce from string if needed
    if isinstance(value, int):
        return value
    elif isinstance(value, str):
        try:
            return int(value)
        except (ValueError, TypeError):
            return Error(msg='Unable to parse int from given string.')

    return Error(msg='Unhandled type, could not coerce.')


def strfield(value: Any) -> Union[str, Error]:
    if isinstance(value, str):
        return value

    return Error(msg='Unhandled type')


FIELD_TYPE_MAP = {
    int: intfield,
    str: strfield,
}