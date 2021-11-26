import attr

from cleancat.chausie.ext.attrs import (
    schema_def_from_attrs_class,
    schema_for_attrs_class,
)
from cleancat.chausie.field import Error, ValidationError
from cleancat.chausie.schema_definition import SchemaDefinition, clean


def test_basic():
    @attr.frozen()
    class AnnotatedValue:
        value: int
        unit: str

    annotated_value_schema_def: SchemaDefinition = schema_def_from_attrs_class(
        AnnotatedValue
    )
    result = clean(
        annotated_value_schema_def, data={'value': 10, 'unit': 'inches'}
    )
    assert isinstance(result, dict)
    assert result['value'] == 10
    assert result['unit'] == 'inches'


def test_implicit_validators():
    @attr.frozen()
    class AnnotatedValue:
        value: int
        unit: str

    annotated_value_schema_def: SchemaDefinition = schema_def_from_attrs_class(
        AnnotatedValue
    )

    # parses str -> int
    result = clean(
        annotated_value_schema_def, data={'value': '10', 'unit': 'inches'}
    )
    assert isinstance(result, dict)
    assert result['value'] == 10
    assert result['unit'] == 'inches'

    # bad string results in an error
    result = clean(
        annotated_value_schema_def, data={'value': 'ten', 'unit': 'inches'}
    )
    assert isinstance(result, ValidationError)
    assert result.errors == [
        Error(field=('value',), msg='Unable to parse int from given string.')
    ]


def test_attr_validators():
    @attr.frozen()
    class AnnotatedValue:
        value: int = attr.attrib(validator=(attr.validators.instance_of(int)))
        unit: str

    annotated_value_schema_def: SchemaDefinition = schema_def_from_attrs_class(
        AnnotatedValue
    )

    # parses str -> int
    result = clean(
        annotated_value_schema_def, data={'value': '10', 'unit': 'inches'}
    )
    assert isinstance(result, dict)
    assert result['value'] == 10
    assert result['unit'] == 'inches'

    # bad string results in an error
    result = clean(
        annotated_value_schema_def, data={'value': 'ten', 'unit': 'inches'}
    )
    assert isinstance(result, ValidationError)
    assert result.errors == [
        Error(field=('value',), msg='Unable to parse int from given string.')
    ]


def test_schema_from_attrs_class():
    @attr.frozen()
    class AnnotatedValue:
        value: int
        unit: str

    AnnotatedValueSchema = schema_for_attrs_class(AnnotatedValue)
    result = AnnotatedValueSchema.clean(data={'value': '10', 'unit': 'inches'})
    assert isinstance(result, AnnotatedValue)
    assert result.value == 10
    assert result.unit == 'inches'
