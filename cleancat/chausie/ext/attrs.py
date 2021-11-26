from typing import Type
import attr
from cleancat.chausie.consts import empty
from cleancat.chausie.field import (
    Error,
    Field,
    Optional,
    Required,
    ValidationError,
)
from cleancat.chausie.schema import Schema, field_def_from_annotation

from cleancat.chausie.schema_definition import (
    SchemaDefinition,
    clean as clean_schema,
)


def convert_attrib_to_field(attrib: attr.Attribute) -> Field:
    """Convert attr Attribute to cleanchausie Field."""
    if attrib.type:
        field = field_def_from_annotation(attrib.type)
    else:
        return Field(
            validators=(),
            accepts=(),
            nullability=Required(),
            depends_on=(),
            serialize_to=None,
            serialize_func=lambda v: v,
        )

    if attrib.default:
        nullability = Optional(omitted_value=attrib.default)
        field = attr.evolve(field, nullability=nullability)

    if attrib.validator:

        def _validate(value):
            try:
                # no ability to validate against other values on the
                # instance (since no instance exists yet), but should
                # support simple validation cases.
                attrib.validator(None, attrib, value)
                return value
            except Exception as e:
                return Error(msg=str(e))

        new_validators = (field.validators or ()) + (_validate,)
        field = attr.evolve(field, validators=new_validators)

    return field


def schema_def_from_attrs_class(attrs_klass: Type) -> SchemaDefinition:
    return SchemaDefinition(
        fields={
            attr_field.name: convert_attrib_to_field(attr_field)
            for attr_field in attr.fields(attrs_klass)
        }
    )


def schema_for_attrs_class(attrs_klass: Type) -> Schema:
    schema_definition = schema_def_from_attrs_class(attrs_klass=attrs_klass)

    class AttrsSchema:
        _schema_definition = schema_definition

        @classmethod
        def clean(cls, data, context=empty):
            result = clean_schema(schema_definition, data, context)
            if isinstance(result, ValidationError):
                return result
            else:
                return attrs_klass(**result)

    return type(
        f'{attrs_klass.__name__}Schema',
        (
            AttrsSchema,
            Schema,
        ),
        {},
    )
