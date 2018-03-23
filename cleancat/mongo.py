"""
This module contains CleanCat fields specific to MongoEngine. ME is not
a required dependency, hence to use these fields, you'll have to import
them via `from cleancat.mongo import ...`.
"""

from mongoengine import ValidationError as MongoValidationError

from .base import (
    Embedded, EmbeddedReference, Field, ReferenceNotFoundError,
    ValidationError, str_type
)


class MongoEmbedded(Embedded):
    """
    Represents MongoEngine's EmbeddedDocument. Expects the document's
    contents as an input dict.
    """
    def __init__(self, document_class=None, *args, **kwargs):
        self.document_class = document_class
        super(MongoEmbedded, self).__init__(*args, **kwargs)

    def clean(self, value):
        """Clean the provided dict of values and then return an
        EmbeddedDocument instantiated with them.
        """
        value = super(MongoEmbedded, self).clean(value)
        return self.document_class(**value)


class MongoEmbeddedReference(EmbeddedReference):
    """
    Represents an embedded reference where the object class is a MongoEngine
    document.

    Examples of passed data and how it's handled:
    {'id': 'existing_id', 'foo': 'bar'} -> updates an existing document
    {'id': 'non-existing_id', 'foo': 'bar'} -> fails bcos the PK is not valid
    {'foo': 'bar'} -> creates a new document instance
    """

    def fetch_existing(self, pk):
        doc_cls = self.object_class
        try:
            return doc_cls.objects.get(pk=pk)
        except doc_cls.DoesNotExist:
            raise ReferenceNotFoundError
        except MongoValidationError as e:
            raise ValidationError(str(e))

    def get_orig_data_from_existing(self, obj):
        # Get a dict of existing document's field names and values.
        if hasattr(obj, 'to_dict'):
            # MongoMallard
            return obj.to_dict()
        else:
            # Upstream MongoEngine
            return dict(obj._data)


class MongoReference(Field):
    """
    Represents a reference. Expects the ID as input.
    Example document: ReferenceField(Doc)
    """

    base_type = str_type

    def __init__(self, document_class=None, **kwargs):
        self.document_class = document_class
        super(MongoReference, self).__init__(**kwargs)

    def clean(self, value):
        value = super(MongoReference, self).clean(value)
        try:
            return self.document_class.objects.get(pk=value)
        except self.document_class.DoesNotExist:
            raise ValidationError('Object does not exist.')

    def serialize(self, value):
        if value:
            return value.pk
