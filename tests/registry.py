import pytest

from cleancat import Schema, String
from cleancat.registry import SchemaNotRegistered, get_schema_by_name


def test_get_existing_schema_from_registry():
    class BookSchema(Schema):
        title = String()

    rv = get_schema_by_name('BookSchema')
    assert rv == BookSchema


def test_schema_missing_from_registry():
    with pytest.raises(SchemaNotRegistered):
        get_schema_by_name('MissingSchema')
