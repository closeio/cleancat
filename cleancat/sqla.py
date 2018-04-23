"""
This module contains CleanCat fields specific to SQLAlchemy. SQLA is not
a required dependency, hence to use these fields, you'll have to import
them via `from cleancat.sqla import ...`.
"""

from sqlalchemy import inspect

from .base import EmbeddedReference, Reference, ReferenceNotFoundError


def object_as_dict(obj):
    """Turn an SQLAlchemy model into a dict of field names and values.

    Based on https://stackoverflow.com/a/37350445/1579058
    """
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}


class SQLAEmbeddedReference(EmbeddedReference):
    """
    Represents an embedded reference where the object class is an SQLAlchemy
    model.

    Examples of passed data and how it's handled:
    {'id': 'existing_id', 'foo': 'bar'} -> updates an existing model
    {'id': 'non-existing_id', 'foo': 'bar'} -> fails bcos the ID is not valid
    {'foo': 'bar'} -> creates a new model instance
    """

    def fetch_existing(self, pk):
        model_cls = self.object_class
        model = model_cls.query.get(pk)
        if not model:
            raise ReferenceNotFoundError
        return model

    def get_orig_data_from_existing(self, obj):
        return object_as_dict(obj)


class SQLAReference(Reference):
    """
    Represents a reference to an SQLAlchemy model. Expects an ID string as
    input and returns a cleaned model instance (verifying that it exists
    first).
    """

    def __init__(self, object_class, pk_field='id', **kwargs):
        self.pk_field = pk_field
        super(SQLAReference, self).__init__(object_class, **kwargs)

    def fetch_object(self, model_id):
        """Fetch the model by its ID."""
        pk_field_instance = getattr(self.object_class, self.pk_field)
        qs = self.object_class.query.filter(pk_field_instance == model_id)
        model = qs.one_or_none()
        if not model:
            raise ReferenceNotFoundError
        return model

    def serialize(self, obj):
        if obj:
            return getattr(obj, self.pk_field)
