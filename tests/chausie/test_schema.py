from typing import Optional, Union, List

import attr
import pytest
from cleancat.base import Bool, Integer, String, List as OldCCList

from cleancat.chausie.consts import omitted
from cleancat.chausie.schema import Schema
from cleancat.chausie.field import (
    field,
    Error,
    ValidationError,
    strfield,
)


class TestAutodef:
    def test_int_basic(self):
        class MySchema(Schema):
            myint: int

        result = MySchema.clean({"myint": 100})
        assert isinstance(result, MySchema)
        assert result.myint == 100
        assert result.serialize() == {"myint": 100}

    def test_optional_omitted(self):
        class MySchema(Schema):
            myint: Optional[int]

        result = MySchema.clean({})
        assert isinstance(result, MySchema)
        assert result.myint is omitted

    def test_optional_none(self):
        class MySchema(Schema):
            myint: Optional[int]

        result = MySchema.clean({"myint": None})
        assert isinstance(result, MySchema)
        assert result.myint is None

    def test_list(self):
        class MySchema(Schema):
            mystrs: List[str]

        result = MySchema.clean({"mystrs": ["a", "b", "c"]})
        assert isinstance(result, MySchema)
        assert result.mystrs == ["a", "b", "c"]


def test_field_dependencies():
    @attr.frozen
    class B:
        val: str

    class UpdateObject(Schema):
        a: str

        @field()
        def b(a: str) -> B:
            return B(val=a)

    result = UpdateObject.clean(data={"a": "A"})
    assert isinstance(result, UpdateObject)
    assert result.a == "A"
    assert result.b == B(val="A")


def test_field_dependencies_error():
    @attr.frozen
    class B:
        val: str

    class UpdateObject(Schema):
        @field()
        def a(value: str) -> Union[str, Error]:
            return Error(msg="nope")

        @field()
        def b(a: str) -> B:
            return B(val=a)

    result = UpdateObject.clean(data={"a": "A"})
    assert isinstance(result, ValidationError)
    assert result.errors == [Error(msg="nope", field=("a",))]


def test_context():
    @attr.frozen
    class Organization:
        pk: str
        name: str

    org_a = Organization(pk="orga_a", name="Organization A")
    org_b = Organization(pk="orga_b", name="Organization B")

    class OrganizationRepo:
        ORGANIZATIONS_BY_PK = {o.pk: o for o in [org_a, org_b]}

        def get_by_pk(self, pk):
            return self.ORGANIZATIONS_BY_PK.get(pk, None)

    @attr.frozen
    class Context:
        org_repo: OrganizationRepo

    class UserSchema(Schema):
        name: str

        @field(parents=(strfield,))
        def organization(value: str, context: Context) -> Union[Organization, Error]:
            org = context.org_repo.get_by_pk(value)
            if org:
                return org

            return Error(msg="Organization not found.")

    context = Context(org_repo=OrganizationRepo())
    result = UserSchema.clean(
        data={"name": "John", "organization": "orga_a"}, context=context
    )
    assert isinstance(result, UserSchema)
    assert result.name == "John"
    assert result.organization == org_a

    result = UserSchema.clean(
        data={"name": "John", "organization": "orga_c"}, context=context
    )
    assert isinstance(result, ValidationError)
    assert result.errors == [
        Error(msg="Organization not found.", field=("organization",))
    ]

    with pytest.raises(ValueError):
        # no context given, ths schema needs a context
        UserSchema.clean(data={"name": "John", "organization": "orga_a"})


def test_def_using_old_fields():
    class MySchema(Schema):
        # base fields
        mystring: str = String()
        mybool: bool = Bool()
        myint: int = Integer()
        mylist: List[str] = OldCCList(String())

        # nullable fields
        nullstring: Optional[str] = String(required=False)
        omittedstring: Optional[str] = String(required=False)


        # old fields can be inter-mixed with new-style fields
        other_string: str

    result = MySchema.clean(
        data={
            "mystring": "asdf",
            "mybool": True,
            "myint": 10,
            "mylist": ["asdf"],
            "nullstring": None,
            # omittedstring isn't present
            "other_string": "the other string",
        }
    )
    assert isinstance(result, MySchema)
    assert result.mystring == "asdf"
    assert result.mybool == True
    assert result.myint == 10
    assert result.mylist == ["asdf"]
    assert result.nullstring is None
    assert result.omittedstring == ""
    assert result.other_string == "the other string"
