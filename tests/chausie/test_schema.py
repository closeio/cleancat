from typing import Optional, Union

import attr
import pytest

from cleancat.chausie.schema import schema, clean, serialize
from cleancat.chausie.field import (
    Optional as CCOptional,
    simple_field,
    intfield,
    field,
    Error,
    ValidationError,
    strfield,
)


def test_autodef():
    @schema
    class MySchema:
        myint: int

    result = clean(MySchema, {'myint': 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert serialize(result) == {'myint': 100}


def test_optional_autodef():
    @schema
    class MySchema:
        myint: Optional[int] = simple_field(
            parents=(intfield,), nullability=CCOptional(omitted_value=None)
        )

    result = clean(MySchema, {})
    assert isinstance(result, MySchema)
    assert result.myint == None


def test_field_dependencies():
    @attr.frozen
    class B:
        val: str

    @schema
    class UpdateObject:
        a: str

        @field()
        def b(a: str) -> B:
            return B(val=a)

    result = clean(schema=UpdateObject, data={'a': 'A'})
    assert isinstance(result, UpdateObject)
    assert result.a == 'A'
    assert result.b == B(val='A')


def test_field_dependencies_error():
    @attr.frozen
    class B:
        val: str

    @schema
    class UpdateObject:
        @field()
        def a(value: str) -> Union[str, Error]:
            return Error(msg='nope')

        @field()
        def b(a: str) -> B:
            return B(val=a)

    result = clean(schema=UpdateObject, data={'a': 'A'})
    assert isinstance(result, ValidationError)
    assert result.errors == [Error(msg='nope', field=('a',))]


def test_context():
    @attr.frozen
    class Organization:
        pk: str
        name: str

    org_a = Organization(pk='orga_a', name='Organization A')
    org_b = Organization(pk='orga_b', name='Organization B')

    class OrganizationRepo:
        ORGANIZATIONS_BY_PK = {o.pk: o for o in [org_a, org_b]}

        def get_by_pk(self, pk):
            return self.ORGANIZATIONS_BY_PK.get(pk, None)

    @attr.frozen
    class Context:
        org_repo: OrganizationRepo

    @schema
    class UserSchema:
        name: str

        @field(parents=(strfield,))
        def organization(
            value: str, context: Context
        ) -> Union[Organization, Error]:
            org = context.org_repo.get_by_pk(value)
            if org:
                return org

            return Error(msg='Organization not found.')

    context = Context(org_repo=OrganizationRepo())
    result = clean(
        schema=UserSchema,
        data={'name': 'John', 'organization': 'orga_a'},
        context=context,
    )
    assert isinstance(result, UserSchema)
    assert result.name == 'John'
    assert result.organization == org_a

    result = clean(
        schema=UserSchema,
        data={'name': 'John', 'organization': 'orga_c'},
        context=context,
    )
    assert isinstance(result, ValidationError)
    assert result.errors == [
        Error(msg='Organization not found.', field=('organization',))
    ]

    with pytest.raises(ValueError):
        # no context given, ths schema needs a context
        clean(
            schema=UserSchema,
            data={'name': 'John', 'organization': 'orga_a'},
        )
