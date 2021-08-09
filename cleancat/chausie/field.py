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
    Collection,
    Type,
)

from cleancat.chausie.consts import OMITTED, omitted, empty


@attr.frozen
class ValidationError:
    errors: List['Error']


@attr.frozen
class Error:
    msg: str
    field: Tuple[str, ...] = tuple()


@attr.frozen
class Errors:
    errors: List[Error]
    field: Tuple[Union[str, int], ...] = tuple()

    def flatten(self) -> List[Error]:
        return [
            wrap_result(field=self.field, result=err) for err in self.errors
        ]


T = TypeVar('T')


@attr.frozen
class Value(Generic[T]):
    value: T


@attr.frozen
class UnvalidatedWrappedValue:
    value: Collection
    inner_field: 'Field'

    construct: Callable
    """Called to construct the wrapped type with validated data."""


class Nullability:
    allow_none: bool


@attr.frozen
class Required(Nullability):
    allow_none: bool = False


@attr.frozen
class Optional(Nullability):
    allow_none: bool = True
    omitted_value: Any = omitted


def wrap_result(field: Tuple[str, ...], result: Any) -> Union[Value, Error]:
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
    """If provided overrides the name of the field during serialization."""

    serialize_func: T_Optional[Callable]
    """If provided, will be used when serializing this field."""

    nullability: Nullability

    depends_on: Tuple[str, ...]
    """Other fields on the same schema this field depends on"""

    def run_validators(
        self,
        field: Tuple[Union[str, int], ...],
        value: Any,
        context: Any,
        intermediate_results: Dict[str, Any],
    ) -> Union[Value, Errors]:
        def _get_deps(func):
            return {
                param for param in inspect.signature(func).parameters.keys()
            }

        # handle nullability
        if value in (omitted, None) and any(
            ['value' in _get_deps(v) for v in self.validators]
        ):
            if value is None:
                if self.nullability.allow_none:
                    return Value(value)
                else:
                    return Errors(
                        field=field,
                        errors=[
                            Error(
                                msg='Value is required, and must not be None.'
                            )
                        ],
                    )

            if isinstance(self.nullability, Required):
                return Errors(
                    field=field, errors=[Error(msg='Value is required.')]
                )
            elif isinstance(self.nullability, Optional):
                return Value(self.nullability.omitted_value)
            else:
                raise TypeError

        def inject_deps(func, val):
            deps = _get_deps(func)
            if not deps:
                return func

            # an empty context default value means its optional/passthrough
            if (
                'context' in deps
                and context is empty
                and inspect.signature(func).parameters['context'].default
                is not empty
            ):
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
            if isinstance(result, Errors):
                return Errors(field=field, errors=result.flatten())
            elif isinstance(result, Error):
                return Errors(field=field, errors=[result])
            elif isinstance(result, UnvalidatedWrappedValue):
                inner_results = [
                    result.inner_field.run_validators(
                        field=(idx,),
                        value=inner_value,
                        context=context,
                        intermediate_results=intermediate_results,
                    )
                    for idx, inner_value in enumerate(result.value)
                ]
                errors = Errors(
                    field=field,
                    errors=[r for r in inner_results if isinstance(r, Error)],
                )
                if errors.errors:
                    return errors
                else:
                    # construct result with the validated inner data
                    result = result.construct(inner_results)

        return wrap_result(field=field, result=result)


V = TypeVar('V')


def noop(value: V) -> V:
    return value


def field(
    *,
    parents: Tuple[Callable, ...] = tuple(),
    accepts: Tuple[str, ...] = tuple(),
    serialize_to: T_Optional[str] = None,
    serialize_func: Callable = noop,
    nullability: Nullability = Required(),
) -> Callable[[Callable], Field]:
    """Defines a Field.

    Args:
        parents: Optionally a list of any parent fields. Validated values chain between
            parents in order they've been given here, before being passed to this
            field's validation function.
        accepts: Optionally a list of field names to accept values from. If not given,
            defaults to the field name on the schema. Field names given first are given
            precedent.
        serialize_to: The field name to serialize to. Defaults to the field name on the
            schema.
        serialize_func: Optionally a function that transforms the serialized value
            during serialization. Defaults to noop, which passes through the value
            unchanged.
        nullability: An instance of one of `Nullability`'s descendants, used to define
            behavior if a field is omitted or falsy. Defaults to Required.
    """

    def _outer_field(inner_func: Callable) -> Field:
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
    """Simple string coercion/validation for int values."""
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
    """Simple validation for str values."""
    if isinstance(value, str):
        return value

    return Error(msg='Unhandled type')


class WrapperField:
    inner_field: Field

    def __init__(self, inner_field: Field):
        self.inner_field = inner_field

    def __call__(self, value: Any) -> Union[UnvalidatedWrappedValue, Error]:
        result = self.impl(value)
        if not isinstance(result, Error):
            return UnvalidatedWrappedValue(
                inner_field=self.inner_field,
                construct=self.construct,
                value=value,
            )

    def impl(self, value: Any):
        raise NotImplementedError()

    def construct(self, values: List[Value]) -> Any:
        raise NotImplementedError()


class _ListField(WrapperField):
    def impl(self, value: Any) -> Union[List, Error]:
        if isinstance(value, tuple):
            value = list(value)

        if isinstance(value, list):
            return value

        return Error(msg='Unhandled type')

    def construct(self, values: List[Value]) -> List:
        return [v.value for v in values]


# alias for consistency with other fields
listfield = _ListField


SchemaCls = TypeVar('SchemaCls')


class _NestedField:
    inner_schema: Type[SchemaCls]

    def __init__(self, schema: Type[SchemaCls]):
        self.inner_schema = schema

    def __call__(
        self, value: Any, context: Any = empty
    ) -> Union[SchemaCls, Errors]:
        from cleancat.chausie.schema import clean

        result = clean(self.inner_schema, value, context=context)
        if isinstance(result, ValidationError):
            return Errors(errors=result.errors)
        elif isinstance(result, self.inner_schema):
            return result

        raise TypeError


nestedfield = _NestedField

FIELD_TYPE_MAP = {
    int: intfield,
    str: strfield,
}
