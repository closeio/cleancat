"""
This module contains CleanCat fields specific to MongoEngine. ME is not
a required dependency, hence to use these fields, you'll have to import
them via `from cleancat.mongo import ...`.
"""

from mongoengine import ValidationError as MongoValidationError

from .base import (
    Embedded, EmbeddedReference, Reference, ReferenceNotFoundError,
    ValidationError
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
        if getattr(obj, 'to_dict', None):
            # MongoMallard
            return obj.to_dict()
        else:
            # Upstream MongoEngine
            return dict(obj._data)


class MongoReference(Reference):
    """
    Represents a reference to a MongoEngine document. Expects an ID string as
    input and returns a cleaned document instance (verifying that it exists
    first).
    """

    def fetch_object(self, doc_id):
        """Fetch the document by its PK."""
        try:
            return self.object_class.objects.get(pk=doc_id)
        except self.object_class.DoesNotExist:
            raise ReferenceNotFoundError

    def serialize(self, doc):
        if doc:
            return doc.pk
