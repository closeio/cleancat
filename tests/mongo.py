import unittest

from mongoengine import Document, StringField, connect

from cleancat import Schema
from cleancat.mongo import MongoReference
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


if __name__ == '__main__':
    unittest.main()
