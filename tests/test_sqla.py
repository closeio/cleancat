import pytest
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from cleancat import Integer, Schema, StopValidation, String, ValidationError
from cleancat.sqla import SQLAEmbeddedReference, SQLAReference, object_as_dict


Base = declarative_base()


class Person(Base):
    __tablename__ = "cleancattest"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String)
    age = sa.Column(sa.Integer)


@pytest.fixture
def sqla_session():
    """Set up an SQLA connection, create all tables, and return a session."""
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = scoped_session(sessionmaker(bind=engine))
    Person.query = session.query_property()
    return session


def test_object_as_dict():
    steve = Person(name="Steve", age=30)
    assert object_as_dict(steve) == {"id": None, "age": 30, "name": "Steve"}


@pytest.mark.usefixtures("sqla_session")
class TestSQLAReferenceField:
    def test_it_updates_an_existing_instance(self, sqla_session):
        steve = Person(name="Steve", age=30)
        sqla_session.add(steve)
        sqla_session.commit()

        clean_val = SQLAReference(Person).clean(str(steve.id))
        assert isinstance(clean_val, Person)
        assert clean_val.id == steve.id

    def test_updating_missing_instance_fails(self):
        expected_err_msg = "Object does not exist."
        with pytest.raises(ValidationError, match=expected_err_msg):
            SQLAReference(Person).clean("id-that-does-not-exist")

    def test_it_can_be_optional(self):
        field = SQLAReference(Person, required=False)
        with pytest.raises(StopValidation) as e:
            field.clean(None)
        assert e.value.args[0] is None


@pytest.mark.usefixtures("sqla_session")
class TestSchemaWithSQLAEmbeddedReference:
    @pytest.fixture
    def book_schema_cls(self):
        class PersonSchema(Schema):
            name = String()
            age = Integer()

        class BookSchema(Schema):
            author = SQLAEmbeddedReference(
                Person, PersonSchema, required=False
            )
            title = String(required=False)

        return BookSchema

    def test_it_creates_a_new_instance(self, book_schema_cls):
        schema = book_schema_cls({"author": {"name": "New Author", "age": 30}})
        data = schema.full_clean()
        author = data["author"]
        assert isinstance(author, Person)
        assert not author.id
        assert author.name == "New Author"
        assert author.age == 30

    def test_it_updates_an_existing_instance(
        self, book_schema_cls, sqla_session
    ):
        steve = Person(name="Steve", age=30)
        sqla_session.add(steve)
        sqla_session.commit()

        schema = book_schema_cls(
            {"author": {"id": str(steve.id), "name": "Updated", "age": 50}}
        )
        data = schema.full_clean()
        author = data["author"]
        assert isinstance(author, Person)
        assert author.id == steve.id
        assert author.name == "Updated"
        assert author.age == 50

    def test_updating_missing_instance_fails(self, book_schema_cls):
        schema = book_schema_cls(
            {"author": {"id": 123456789, "name": "Arbitrary Non-existent ID"}}
        )
        pytest.raises(ValidationError, schema.full_clean)
        assert schema.field_errors == {"author": "Object does not exist."}

    def test_it_can_be_optional(self, book_schema_cls):
        schema = book_schema_cls(
            {"title": "Book without an author", "author": None}
        )
        data = schema.full_clean()
        assert data == {"title": "Book without an author", "author": None}
