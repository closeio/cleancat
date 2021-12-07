import datetime
import functools
import inspect
import itertools
import re
from enum import Enum

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
    overload,
    TYPE_CHECKING,
)

try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol

from dateutil import parser

from cleancat.chausie.consts import omitted, empty

if TYPE_CHECKING:
    from .schema import Schema


@attr.frozen
class ValidationError:
    errors: List["Error"]


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


T = TypeVar("T")


@attr.frozen
class Value(Generic[T]):
    value: T


@attr.frozen
class UnvalidatedWrappedValue:
    value: Collection
    inner_field: "Field"

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


@overload
def wrap_result(field: Tuple[Union[str, int], ...], result: Error) -> Error:
    ...


@overload
def wrap_result(field: Tuple[Union[str, int], ...], result: Value) -> Value:
    ...


def wrap_result(
    field: Tuple[Union[str, int], ...], result: Any
) -> Union[Value, Error]:
    if isinstance(result, Error):
        return attr.evolve(result, field=field + result.field)
    elif not isinstance(result, Value):
        return Value(value=result)
    return result


FType = TypeVar("FType")


@attr.frozen
class Field(Generic[FType]):
    validators: Tuple[Callable, ...]
    """Callable that validate a the given field's value."""

    accepts: Tuple[str, ...]
    """Field names accepted when parsing unvalidated input.

    If left unspecified, effectively defaults to the name of the attribute
    defined on the schema.
    """

    serialize_to: T_Optional[str]
    """If provided overrides the name of the field during serialization."""

    serialize_func: Callable
    """Used when serializing this field. Defaults to a noop passthrough."""

    nullability: Nullability

    depends_on: Tuple[str, ...]
    """Other fields on the same schema this field depends on"""

    def __get__(self, instance, owner) -> FType:
        return super().__get__(instance, owner)

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
            ["value" in _get_deps(v) for v in self.validators]
        ):
            if value is None:
                if self.nullability.allow_none:
                    return Value(value)
                else:
                    return Errors(
                        field=field,
                        errors=[
                            Error(
                                msg="Value is required, and must not be None."
                            )
                        ],
                    )

            if isinstance(self.nullability, Required):
                return Errors(
                    field=field, errors=[Error(msg="Value is required.")]
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
                "context" in deps
                and context is empty
                and inspect.signature(func).parameters["context"].default
                is not empty
            ):
                raise ValueError(
                    "Context is required for evaluating this schema."
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
                    for dep, v in {"context": context, "value": val}.items()
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
                flattened_errors = []
                for r in inner_results:
                    if isinstance(r, Error):
                        flattened_errors.append(r)
                    elif isinstance(r, Errors):
                        flattened_errors.extend(r.flatten())
                errors = Errors(field=field, errors=flattened_errors)
                if errors.errors:
                    return errors
                else:
                    # construct result with the validated inner data
                    result = result.construct(inner_results)

        return wrap_result(field=field, result=result)


V = TypeVar("V")


def noop(value: V) -> V:
    return value


class InnerFieldProto(Protocol[FType]):
    @overload
    def __call__(self) -> Field[FType]:
        ...

    @overload
    def __call__(
        self, inner_func: Union[Callable[..., FType], Field[FType]]
    ) -> Field[FType]:
        ...

    def __call__(
        self,
        inner_func: Union[Callable[..., FType], Field[FType], None] = None,
    ) -> Field[FType]:
        ...


# when decorating a function (decorated func is passed to the inner func)
@overload
def field(
    *,
    parents: Tuple[Union[Callable[..., FType], Field[FType]], ...] = tuple(),
    accepts: Tuple[str, ...] = tuple(),
    serialize_to: T_Optional[str] = None,
    serialize_func: Callable = noop,
    nullability: Nullability = Required(),
) -> InnerFieldProto[FType]:
    ...


# defining simple fields with existing functions
@overload
def field(
    decorated_func: Callable[..., FType],
    *,
    parents: Tuple[Union[Callable, Field], ...] = tuple(),
    accepts: Tuple[str, ...] = tuple(),
    serialize_to: T_Optional[str] = None,
    serialize_func: Callable = noop,
    nullability: Nullability = Required(),
) -> Field[FType]:
    ...


def field(
    decorated_func: T_Optional[Union[Callable, Field]] = None,
    *,
    parents: Tuple[Union[Callable, Field], ...] = tuple(),
    accepts: Tuple[str, ...] = tuple(),
    serialize_to: T_Optional[str] = None,
    serialize_func: Callable = noop,
    nullability: Nullability = Required(),
) -> Union[Callable[[Callable], Field], Field]:
    """Defines a Field.

    Args:
        parents: Optionally a list of any parent fields. Validated values chain between
            parents in order they've been given here, before being passed to this
            field's validation function. Note that if a `Field` is given instead of a
            `Callable`, only the validators are reused.
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

    def _outer_field(inner_func: Union[Callable, Field, None] = None) -> Field:
        # flatten any parents defined as fields
        validators: List[Callable] = []
        for p in parents + (inner_func or noop,):
            if isinstance(p, Field):
                validators.extend(p.validators)
            else:
                validators.append(p)

        # find any declared dependencies on other fields
        deps = {
            n
            for n in itertools.chain(
                *[inspect.signature(f).parameters.keys() for f in validators]
            )
            if n not in {"context", "value"}
        }
        return Field(
            nullability=nullability,
            validators=tuple(validators),
            accepts=accepts,
            serialize_to=serialize_to,
            serialize_func=serialize_func,
            depends_on=tuple(deps),
        )

    if decorated_func is not None:
        return _outer_field(inner_func=decorated_func)
    else:
        return _outer_field


def intfield(value: Any) -> Union[int, Error]:
    """Simple string coercion/validation for int values."""
    # coerce from string if needed
    if isinstance(value, int):
        return value
    elif isinstance(value, str):
        try:
            return int(value)
        except (ValueError, TypeError):
            return Error(msg="Unable to parse int from given string.")

    return Error(msg="Unhandled type, could not coerce.")


def strfield(value: Any) -> Union[str, Error]:
    """Simple validation for str values."""
    if isinstance(value, str):
        return value

    return Error(msg="Unhandled type")


class WrapperField:
    inner_field: Field

    def __init__(self, inner_field: Field):
        self.inner_field = inner_field

    def __call__(
        self, value: Any
    ) -> Union[UnvalidatedWrappedValue, Error, Errors]:
        result = self.impl(value)
        if not isinstance(result, (Error, Errors)):
            return UnvalidatedWrappedValue(
                inner_field=self.inner_field,
                construct=self.construct,
                value=value,
            )
        return result

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

        return Error(msg="Unhandled type")

    def construct(self, values: List[Value]) -> List:
        return [v.value for v in values]


# alias for consistency with other fields
listfield = _ListField


class _NestedField:
    inner_schema: Type["Schema"]

    def __init__(self, schema: Type["Schema"]):
        self.inner_schema = schema

    def __call__(
        self, value: Any, context: Any = empty
    ) -> Union["Schema", Errors]:
        result = self.inner_schema.clean(value, context=context)
        if isinstance(result, ValidationError):
            return Errors(errors=result.errors)
        elif isinstance(result, self.inner_schema):
            return result

        raise TypeError


nestedfield = _NestedField

EnumCls = TypeVar("EnumCls", bound=Enum)


class _EnumField(Generic[EnumCls]):
    enum_cls: Type[EnumCls]

    def __init__(self, enum_cls: Type[EnumCls]):
        self.enum_cls = enum_cls

    def __call__(self, value: Any) -> Union[EnumCls, Error]:
        try:
            return self.enum_cls(value)
        except (ValueError, TypeError):
            return Error(msg="Invalid value for enum.")


enumfield = _EnumField


def regexfield(regex: str, flags: int = 0) -> Field:
    _compiled_regex = re.compile(regex, flags)

    def _validate_regex(value: str) -> Union[str, Error]:
        if not _compiled_regex.match(value):
            return Error(msg="Invalid input.")
        return value

    return field(_validate_regex, parents=(strfield,))


@field(parents=(strfield,))
def datetimefield(value: str) -> Union[datetime.datetime, Error]:
    # TODO should this reject naive datetimes? or assume a timezone?
    try:
        # TODO should we use ciso8601 to parse? It's a bit stricter, but much faster.
        return parser.parse(value)
    except ValueError:
        return Error(msg="Could not parse datetime.")


def boolfield(value: Any) -> Union[bool, Error]:
    if not isinstance(value, bool):
        return Error(msg="Value is not a boolean.")
    return value


def urlfield(
    require_tld=True,
    default_scheme=None,
    allowed_schemes=None,
    disallowed_schemes=None,
) -> Field:
    def normalize_scheme(sch):
        if sch.endswith("://") or sch.endswith(":"):
            return sch
        return sch + "://"

    # FQDN validation similar to https://github.com/chriso/validator.js/blob/master/src/lib/isFQDN.js

    # ff01-ff5f -> full-width chars, not allowed
    alpha_numeric_and_symbols_ranges = "0-9a-z\u00a1-\uff00\uff5f-\uffff"

    tld_part = (
        require_tld
        and r"\.[%s-]{2,63}" % alpha_numeric_and_symbols_ranges
        or ""
    )
    scheme_part = "[a-z]+://"
    if default_scheme:
        default_scheme = normalize_scheme(default_scheme)
    scheme_regex = re.compile("^" + scheme_part, re.IGNORECASE)
    if default_scheme:
        scheme_part = "(%s)?" % scheme_part
    regex = (
        r"^%s([-%s@:%%_+.~#?&/\\=]{1,256}%s|([0-9]{1,3}\.){3}[0-9]{1,3})(:[0-9]+)?([/?].*)?$"
        % (scheme_part, alpha_numeric_and_symbols_ranges, tld_part)
    )
    regex_flags = re.IGNORECASE | re.UNICODE

    def compile_schemes_to_regexes(schemes):
        return [
            re.compile("^" + normalize_scheme(sch) + ".*", re.IGNORECASE)
            for sch in schemes
        ]

    allowed_schemes = allowed_schemes or []
    allowed_schemes_regexes = compile_schemes_to_regexes(allowed_schemes)

    disallowed_schemes = disallowed_schemes or []
    disallowed_schemes_regexes = compile_schemes_to_regexes(disallowed_schemes)

    @field(parents=(regexfield(regex=regex, flags=regex_flags),))
    def _urlfield(value: str) -> Union[Error, str]:
        if not scheme_regex.match(value):
            value = default_scheme + value

        if allowed_schemes:
            if not any(
                allowed_regex.match(value)
                for allowed_regex in allowed_schemes_regexes
            ):
                allowed_schemes_text = " or ".join(allowed_schemes)
                return Error(
                    msg=(
                        "This URL uses a scheme that's not allowed. You can only "
                        f"use {allowed_schemes_text}."
                    )
                )

        if disallowed_schemes:
            if any(
                disallowed_regex.match(value)
                for disallowed_regex in disallowed_schemes_regexes
            ):
                return Error(msg="This URL uses a scheme that's not allowed.")

        return value

    return _urlfield


def emailfield(max_length=254) -> Field:
    email_regex = (
        r'^(?:[^\.@\s]|[^\.@\s]\.(?!\.))*[^.@\s]@'
        r'[^.@\s](?:[^\.@\s]|\.(?!\.))*\.[a-z]{2,63}$'
    )
    regex_flags = re.IGNORECASE

    def _email_field(value: str) -> str:
        # trim any leading/trailing whitespace before validating the email
        ret = value.strip()

        # only allow up to max_length
        if len(ret) > max_length:
            return Error(f"Email exceeds max length of {max_length}")

        return ret

    return field(
        noop,
        parents=(
            strfield,
            _email_field,
            regexfield(regex=email_regex, flags=regex_flags),
        ),
    )


FIELD_TYPE_MAP = {
    int: intfield,
    str: strfield,
    bool: boolfield,
    datetime.datetime: datetimefield,
}

# TODO
#  email
#  dict? Should we should even support these?
#  trimmedstring?
