import pytest
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from cleancat import Integer, Schema, StopValidation, String, ValidationError
from cleancat.sqla import SQLAEmbeddedReference, SQLAReference, object_as_dict


@pytest.fixture
def decl_base():
    return declarative_base()


@pytest.fixture
def person_cls(decl_base):
    class Person(decl_base):
        __tablename__ = 'cleancattest'
        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String)
        age = sa.Column(sa.Integer)
    return Person


@pytest.fixture
def sqla_session(decl_base, person_cls):
    """Set up an SQLA connection, create all tables, and return a session."""
    engine = sa.create_engine('sqlite:///:memory:')
    decl_base.metadata.create_all(engine)
    session = scoped_session(sessionmaker(bind=engine))

    # Set up a ModelClass.query "shortcut" property for all models.
    person_cls.query = session.query_property()

    return session


def test_object_as_dict(person_cls):
    steve = person_cls(name='Steve', age=30)
    assert object_as_dict(steve) == {
        'id': None,
        'age': 30,
        'name': 'Steve'
    }


@pytest.mark.usefixtures('sqla_session')
class TestSQLAReferenceField:

    def test_it_updates_an_existing_instance(self, person_cls, sqla_session):
        steve = person_cls(name='Steve', age=30)
        sqla_session.add(steve)
        sqla_session.commit()

        clean_val = SQLAReference(person_cls).clean(str(steve.id))
        assert isinstance(clean_val, person_cls)
        assert clean_val.id == steve.id

    def test_updating_missing_instance_fails(self, person_cls):
        with pytest.raises(ValidationError) as e:
            SQLAReference(person_cls).clean('id-that-does-not-exist')
        assert unicode(e.value) == 'Object does not exist.'

    def test_it_can_be_optional(self, person_cls):
        field = SQLAReference(person_cls, required=False)
        with pytest.raises(StopValidation) as e:
            field.clean(None)
        assert e.value.args[0] is None


@pytest.mark.usefixtures('sqla_session')
class TestSchemaWithSQLAEmbeddedReference:

    @pytest.fixture
    def schema_cls(self, person_cls):
        class PersonSchema(Schema):
            name = String()
            age = Integer()

        class BookSchema(Schema):
            author = SQLAEmbeddedReference(person_cls, PersonSchema)
            title = String(required=False)

        return BookSchema

    def test_it_creates_a_new_instance(self, schema_cls, person_cls):
        schema = schema_cls({
            'author': {
                'name': 'New Author',
                'age': 30
            }
        })
        data = schema.full_clean()
        author = data['author']
        assert isinstance(author, person_cls)
        assert not author.id
        assert author.name == 'New Author'
        assert author.age == 30

    def test_it_updates_an_existing_instance(self, schema_cls, person_cls,
                                             sqla_session):
        steve = person_cls(name='Steve', age=30)
        sqla_session.add(steve)
        sqla_session.commit()

        schema = schema_cls({
            'author': {
                'id': str(steve.id),
                'name': 'Updated',
                'age': 50
            }
        })
        data = schema.full_clean()
        author = data['author']
        assert isinstance(author, person_cls)
        assert author.id == steve.id
        assert author.name == 'Updated'
        assert author.age == 50

    def test_updating_missing_instance_fails(self, schema_cls):
        schema = schema_cls({
            'author': {
                'id': 123456789,
                'name': 'Arbitrary Non-existent ID'
            }
        })
        pytest.raises(ValidationError, schema.full_clean)
        assert schema.field_errors == {'author': 'Object does not exist.'}

    def test_it_can_be_optional(self, schema_cls):
        schema_cls.author.required = False
        schema = schema_cls({
            'title': 'Book without an author',
            'author': None
        })
        data = schema.full_clean()
        assert data == {
            'title': 'Book without an author',
            'author': None
        }
