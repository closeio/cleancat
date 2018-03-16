"""
This module contains CleanCat fields specific to MongoEngine. ME is not
a required dependency, hence to use these fields, you'll have to import
them via `from cleancat.mongo import ...`.
"""

from mongoengine import ValidationError as MongoValidationError

from .base import Dict, Embedded, Field, ValidationError


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


class MongoEmbeddedReference(MongoEmbedded):
    """
    Represents a MongoEngine document, which can be created or updated based
    on a provided dict of values.

    The name of the field that acts as the primary key of the document can be
    specified using pk_field (it's 'id' by default). If the passed document
    contains the pk_field, we check if a document with that PK exists and then
    we update its fields (or fail if it can't be found). If the input dict
    does not contain the pk_field, it is assumed that a new document should be
    created.

    Examples:
    {'id': 'existing_id', 'foo': 'bar'} -> valid (updates an existing document)
    {'id': 'non-existing_id', 'foo': 'bar'} -> invalid
    {'foo': 'bar'} -> valid (creates a new document)
    """

    def __init__(self, *args, **kwargs):
        self.pk_field = kwargs.pop('pk_field', 'id')
        super(MongoEmbeddedReference, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = Dict.clean(self, value)
        if value and self.pk_field in value:
            return self.clean_existing(value)
        return self.clean_new(value)

    def clean_new(self, value):
        """Return a new document instantiated with cleaned data."""
        value = self.schema_class(value).full_clean()
        return self.document_class(**value)

    def clean_existing(self, value):
        """Clean the data and return an existing document with its fields
        updated based on the cleaned values.
        """
        existing_pk = value[self.pk_field]
        try:
            document = self.document_class.objects.get(pk=existing_pk)
        except self.document_class.DoesNotExist:
            raise ValidationError('Object does not exist.')
        except MongoValidationError as e:
            raise ValidationError(str(e))

        # Get a dict of existing document's field names and values.
        if hasattr(document, 'to_dict'):
            # MongoMallard
            document_data = document.to_dict()
        else:
            # Upstream MongoEngine
            document_data = dict(document._data)
        if None in document_data:
            del document_data[None]

        # Clean the data (passing the new data dict and the original data to
        # the schema).
        value = self.schema_class(value, document_data).full_clean()

        # Set cleaned data on the document (except for the pk_field).
        for field_name, field_value in value.items():
            if field_name != self.pk_field:
                setattr(document, field_name, field_value)

        return document


class MongoReference(Field):
    """
    Represents a reference. Expects the ID as input.
    Example document: ReferenceField(Doc)
    """

    base_type = basestring

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
