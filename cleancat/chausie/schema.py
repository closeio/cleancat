import typing
from typing import Dict, TypeVar, Type, Any, Union

from cleancat.chausie.consts import empty
from cleancat.chausie.field import (
    field,
    Field,
    FIELD_TYPE_MAP,
    ValidationError,
    Optional as CCOptional,
    listfield,
)
from cleancat.chausie.schema_definition import (
    SchemaDefinition,
    clean,
    serialize,
)


def _field_def_from_annotation(annotation) -> typing.Optional[Field]:
    """Turn an annotation into an equivalent field.

    Explicitly ignores `ClassVar` annotations, returning None.
    """
    if annotation in FIELD_TYPE_MAP:
        return field(FIELD_TYPE_MAP[annotation])
    elif typing.get_origin(annotation) is Union:
        # basic support for `Optional`
        union_of = typing.get_args(annotation)
        if not (len(union_of) == 2 and type(None) in union_of):
            raise TypeError("Unrecognized type annotation.")

        # yes, we actually do want to check against type(xx)
        NoneType = type(None)
        inner = next(t for t in typing.get_args(annotation) if t is not NoneType)
        if inner in FIELD_TYPE_MAP:
            return field(
                FIELD_TYPE_MAP[inner],
                nullability=CCOptional(),
            )
    elif typing.get_origin(annotation) is list:
        list_of = typing.get_args(annotation)
        if len(list_of) != 1:
            raise TypeError("Only one inner List type is currently supported.")
        inner_field_def = _field_def_from_annotation(list_of[0])
        assert inner_field_def
        return field(listfield(inner_field_def))
    elif typing.get_origin(annotation) is typing.ClassVar:
        # just ignore these, these don't have to become fields
        return None

    raise TypeError("Unrecognized type annotation.")


def _check_for_dependency_loops(fields: Dict[str, Field]) -> None:
    """Try to catch simple top-level dependency loops.

    Does not handle wrapped fields.
    """
    deps = {name: set(f_def.depends_on) for name, f_def in fields.items()}
    seen = {"self"}
    while deps:
        prog = len(seen)
        for f_name, f_deps in deps.items():
            if not f_deps or all([f_dep in seen for f_dep in f_deps]):
                seen.add(f_name)
                deps.pop(f_name)
                break

        if len(seen) == prog:
            # no progress was made
            raise ValueError("Field dependencies could not be resolved.")


class SchemaMetaclass(type):
    def __new__(cls, clsname, bases, attribs, autodef=True):
        """
        Turn a Schema subclass into a schema.

        Args:
            autodef: automatically define simple fields for annotated attributes
        """
        fields = {}
        for base in bases:
            # can't directly check for Schema class, since sometimes it hasn't
            # been created yet
            base_schema_def = getattr(base, "_schema_definition", None)
            if isinstance(base_schema_def, SchemaDefinition):
                fields.update(base_schema_def.fields)
        fields.update(
            {f_name: f for f_name, f in attribs.items() if isinstance(f, Field)}
        )

        if autodef:
            for f_name, f_type in attribs.get("__annotations__", {}).items():
                if f_name not in fields:
                    field_def = _field_def_from_annotation(f_type)
                    if field_def:
                        fields[f_name] = field_def

        # check for dependency loops
        _check_for_dependency_loops(fields)

        schema_def = SchemaDefinition(fields=fields)
        return super(SchemaMetaclass, cls).__new__(
            cls, clsname, bases, {**attribs, "_schema_definition": schema_def}
        )


T = TypeVar("T", bound="Schema")
SchemaVar = TypeVar("SchemaVar", bound="Schema")


class Schema(typing.Generic[T], metaclass=SchemaMetaclass):
    _schema_definition: typing.ClassVar[SchemaDefinition]

    def __init__(self, **kwargs):
        defined_fields = self._schema_definition.fields
        for k, v in kwargs.items():
            if k not in defined_fields:
                continue
            setattr(self, k, v)

    @classmethod
    def clean(
        cls: Type[SchemaVar], data: Any, context: Any = empty
    ) -> Union[SchemaVar, ValidationError]:
        result = clean(cls._schema_definition, data, context)
        if isinstance(result, ValidationError):
            return result
        else:
            return cls(**result)

    def serialize(self) -> Dict:
        return serialize(
            self._schema_definition,
            {n: getattr(self, n) for n in self._schema_definition.fields.keys()},
        )
