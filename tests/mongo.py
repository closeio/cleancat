import unittest

from bson import ObjectId
from mongoengine import Document, StringField, connect

from cleancat import Schema, String, ValidationError
from cleancat.mongo import MongoEmbeddedReference, MongoReference
from cleancat.utils import ValidationTestCase


class MongoValidationTestCase(ValidationTestCase):

    def setUp(self):
        super(MongoValidationTestCase, self).setUp()

        connect(db='cleancat_test')

        class Person(Document):
            name = StringField()

        Person.drop_collection()
        self.Person = Person


class MongoReferenceTestCase(MongoValidationTestCase):

    def test_existing(self):
        class BookSchema(Schema):
            author_id = MongoReference(self.Person)

        doc = self.Person.objects.create(name='Steve')
        self.assertValid(
            BookSchema({'author_id': str(doc.pk)}),
            {'author_id': doc}
        )

    def test_missing(self):
        class BookSchema(Schema):
            author_id = MongoReference(self.Person)

        self.assertInvalid(
            BookSchema({'author_id': str(ObjectId())}),
            {'field-errors': ['author_id']}
        )

    def test_optional(self):
        class BookSchema(Schema):
            title = String()
            author_id = MongoReference(self.Person, required=False)

        schema = BookSchema({
            'title': 'Book without an author',
            'author_id': None
        })
        data = schema.full_clean()
        assert data == {
            'title': 'Book without an author',
            'author_id': None
        }


class MongoEmbeddedReferenceTestCase(MongoValidationTestCase):

    def test_create(self):
        class PersonSchema(Schema):
            name = String()

        class BookSchema(Schema):
            author = MongoEmbeddedReference(self.Person, PersonSchema)

        schema = BookSchema({
            'author': {
                'name': 'New Author'
            }
        })
        data = schema.full_clean()
        author = data['author']
        assert isinstance(author, self.Person)
        assert not author.pk
        assert author.name == 'New Author'

    def test_update(self):
        class PersonSchema(Schema):
            name = String()

        class BookSchema(Schema):
            author = MongoEmbeddedReference(self.Person, PersonSchema)

        doc = self.Person.objects.create(name='Steve')

        schema = BookSchema({
            'author': {
                'id': str(doc.pk),
                'name': 'Updated'
            }
        })
        data = schema.full_clean()
        author = data['author']
        assert isinstance(author, self.Person)
        assert author.pk == doc.pk
        assert author.name == 'Updated'

    def test_update_missing(self):
        class PersonSchema(Schema):
            name = String()

        class BookSchema(Schema):
            author = MongoEmbeddedReference(self.Person, PersonSchema)

        schema = BookSchema({
            'author': {
                'id': str(ObjectId()),
                'name': 'Arbitrary Non-existent Object ID'
            }
        })
        self.assertRaises(ValidationError, schema.full_clean)
        assert schema.field_errors == {'author': 'Object does not exist.'}

    def test_optional(self):
        class PersonSchema(Schema):
            name = String()

        class BookSchema(Schema):
            title = String()
            author = MongoEmbeddedReference(self.Person, PersonSchema,
                                            required=False)

        schema = BookSchema({
            'title': 'Book without an author',
            'author': None
        })
        data = schema.full_clean()
        assert data == {
            'title': 'Book without an author',
            'author': None
        }


if __name__ == '__main__':
    unittest.main()
