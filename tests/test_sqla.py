import unittest

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from cleancat import Integer, Schema, String, ValidationError
from cleancat.sqla import SQLAEmbeddedReference, SQLAReference, object_as_dict


def test_object_as_dict():
    Base = declarative_base()

    class Person(Base):
        __tablename__ = 'cleancattest'
        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String)
        age = sa.Column(sa.Integer)

    steve = Person(name='Steve', age=30)
    assert object_as_dict(steve) == {
        'id': None,
        'age': 30,
        'name': 'Steve'
    }


class SQLABaseTestCase(unittest.TestCase):

    def setUp(self):
        super(SQLABaseTestCase, self).setUp()

        Base = declarative_base()

        class Person(Base):
            __tablename__ = 'cleancattest'
            id = sa.Column(sa.Integer, primary_key=True)
            name = sa.Column(sa.String)
            age = sa.Column(sa.Integer)

        self.Person = Person

        engine = sa.create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        self.session = scoped_session(sessionmaker(bind=engine))
        self.Person.query = self.session.query_property()


class SQLAEmbeddedReferenceTestCase(SQLABaseTestCase):

    def test_create(self):
        class PersonSchema(Schema):
            name = String()
            age = Integer()

        class BookSchema(Schema):
            author = SQLAEmbeddedReference(self.Person, PersonSchema)

        schema = BookSchema({
            'author': {
                'name': 'New Author',
                'age': 30
            }
        })
        data = schema.full_clean()
        author = data['author']
        assert isinstance(author, self.Person)
        assert not author.id
        assert author.name == 'New Author'
        assert author.age == 30

    def test_update(self):
        class PersonSchema(Schema):
            name = String()
            age = Integer()

        class BookSchema(Schema):
            author = SQLAEmbeddedReference(self.Person, PersonSchema)

        steve = self.Person(name='Steve', age=30)
        self.session.add(steve)
        self.session.commit()

        schema = BookSchema({
            'author': {
                'id': str(steve.id),
                'name': 'Updated',
                'age': 50
            }
        })
        data = schema.full_clean()
        author = data['author']
        assert isinstance(author, self.Person)
        assert author.id == steve.id
        assert author.name == 'Updated'
        assert author.age == 50

    def test_update_missing(self):
        class PersonSchema(Schema):
            name = String()
            age = Integer()

        class BookSchema(Schema):
            author = SQLAEmbeddedReference(self.Person, PersonSchema)

        schema = BookSchema({
            'author': {
                'id': 123456789,
                'name': 'Arbitrary Non-existent ID'
            }
        })
        pytest.raises(ValidationError, schema.full_clean)
        assert schema.field_errors == {'author': 'Object does not exist.'}

    def test_optional(self):
        class PersonSchema(Schema):
            name = String()

        class BookSchema(Schema):
            title = String()
            author = SQLAEmbeddedReference(self.Person, PersonSchema,
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


class SQLAReferenceTestCase(SQLABaseTestCase):

    def test_existing(self):
        class BookSchema(Schema):
            title = String()
            author = SQLAReference(self.Person)

        steve = self.Person(name='Steve', age=30)
        self.session.add(steve)
        self.session.commit()

        schema = BookSchema({
            'title': "Steve's Book",
            'author': str(steve.id),
        })
        data = schema.full_clean()
        author = data['author']
        assert isinstance(author, self.Person)
        assert author.id == steve.id

    def test_missing(self):
        class BookSchema(Schema):
            title = String()
            author = SQLAReference(self.Person)

        schema = BookSchema({
            'title': 'Book without an invalid author',
            'author': 'id-that-does-not-exist'
        })
        pytest.raises(ValidationError, schema.full_clean)
        assert schema.field_errors == {'author': 'Object does not exist.'}

    def test_optional(self):
        class BookSchema(Schema):
            title = String()
            author = SQLAReference(self.Person, required=False)

        schema = BookSchema({
            'title': 'Book without an author',
            'author': None
        })
        data = schema.full_clean()
        assert data == {
            'title': 'Book without an author',
            'author': None
        }
