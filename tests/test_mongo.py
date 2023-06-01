import pytest
from bson import ObjectId
from mongoengine import Document, EmbeddedDocument, StringField, connect

from cleancat import Schema, StopValidation, String, ValidationError
from cleancat.mongo import (
    MongoEmbedded,
    MongoEmbeddedReference,
    MongoReference,
)


@pytest.fixture()
def _mongodb():
    connect(db="cleancat_test")


@pytest.fixture()
def person_cls(_mongodb):
    class Person(Document):
        name = StringField()

    Person.drop_collection()
    return Person


class TestMongoEmbedded:
    @pytest.fixture()
    def doc_cls(self):
        class EmbeddedPerson(EmbeddedDocument):
            name = StringField()

        return EmbeddedPerson

    @pytest.fixture()
    def schema_cls(self):
        class EmbeddedPersonSchema(Schema):
            name = String(min_length=2)

        return EmbeddedPersonSchema

    def test_it_accepts_valid_input(self, doc_cls, schema_cls):
        value = {"name": "Jon"}
        assert MongoEmbedded(doc_cls, schema_cls).clean(value) == doc_cls(
            **value
        )

    def test_it_enforces_validation_of_embedded_schema(
        self, doc_cls, schema_cls
    ):
        with pytest.raises(ValidationError) as e:
            MongoEmbedded(doc_cls, schema_cls).clean({"name": "X"})
        assert e.value.args[0] == {
            "errors": [],
            "field-errors": {
                "name": "The value must be at least 2 characters long."
            },
        }


class TestMongoReferenceField:
    def test_it_accepts_an_existing_doc(self, person_cls):
        field = MongoReference(person_cls)
        doc = person_cls.objects.create(name="Steve")
        assert field.clean(str(doc.pk)) == doc

    def test_it_rejects_a_missing_doc(self, person_cls):
        field = MongoReference(person_cls)
        expected_err_msg = "Object does not exist."
        with pytest.raises(ValidationError, match=expected_err_msg):
            field.clean(str(ObjectId()))

    def test_it_can_be_optional(self, person_cls):
        field = MongoReference(person_cls, required=False)
        with pytest.raises(StopValidation) as e:
            field.clean(None)
        assert e.value.args[0] is None

    def test_rejection_with_raw_field_name_in_schema(self, person_cls):
        class BookSchema(Schema):
            author = MongoReference(person_cls, raw_field_name="author_id")

        schema = BookSchema({"author_id": str(ObjectId())})
        pytest.raises(ValidationError, schema.full_clean)
        assert schema.field_errors == {"author_id": "Object does not exist."}


class TestSchemaWithMongoEmbeddedReferenceField:
    @pytest.fixture()
    def schema_cls(self, person_cls):
        class PersonSchema(Schema):
            name = String()

        class BookSchema(Schema):
            author = MongoEmbeddedReference(person_cls, PersonSchema)
            title = String(required=False)

        return BookSchema

    def test_it_creates_a_new_instance(self, schema_cls, person_cls):
        schema = schema_cls({"author": {"name": "New Author"}})
        data = schema.full_clean()
        author = data["author"]
        assert isinstance(author, person_cls)
        assert not author.pk
        assert author.name == "New Author"

    def test_it_updates_an_existing_instance(self, schema_cls, person_cls):
        doc = person_cls.objects.create(name="Steve")
        schema = schema_cls({"author": {"id": str(doc.pk), "name": "Updated"}})
        data = schema.full_clean()
        author = data["author"]
        assert isinstance(author, person_cls)
        assert author.pk == doc.pk
        assert author.name == "Updated"

    def test_updating_missing_instance_fails(self, schema_cls):
        schema = schema_cls(
            {
                "author": {
                    "id": str(ObjectId()),
                    "name": "Arbitrary Non-existent Object ID",
                }
            }
        )
        pytest.raises(ValidationError, schema.full_clean)
        assert schema.field_errors == {"author": "Object does not exist."}

    def test_it_can_be_optional(self, schema_cls):
        schema_cls.author.required = False
        schema = schema_cls(
            {"title": "Book without an author", "author": None}
        )
        data = schema.full_clean()
        assert data == {"title": "Book without an author", "author": None}
