import inspect
import pytest
import attr
import typing
from typing import (
    Generic,
    TypeVar,
    Type,
    Union,
    Dict,
    List,
    Tuple,
    Any,
    Callable,
    Optional as T_Optional,
)
import functools


@attr.frozen
class ValidationError:
    errors: List['Error']


@attr.frozen
class Error:
    msg: str
    field: Tuple[str, ...] = tuple()


class OMITTED:
    """used as singleton for omitted values in validation"""


omitted = OMITTED()


class EMPTY:
    """used as singleton for omitted options/kwargs"""


empty = EMPTY()

T = TypeVar('T')


@attr.frozen
class Value(Generic[T]):
    value: Union[T, OMITTED]  # not sure how to express this


class Nullability:
    pass


class Required(Nullability):
    pass


@attr.frozen
class Optional(Nullability):
    omitted_value: Any = omitted


def intfield(value: Any) -> Union[Value[int], Error]:
    # coerce from string if needed
    if isinstance(value, int):
        return value
    elif isinstance(value, str):
        try:
            return int(value)
        except (ValueError, TypeError):
            return Error(msg='Unable to parse int from given string.')

    return Error(msg='Unhandled type, could not coerce.')


def strfield(value: Any) -> Union[str, Error]:
    if isinstance(value, str):
        return value

    return Error(msg='Unhandled type')


ValueOrError = TypeVar('ValueOrError', bound=Union[Value, Error])


def wrap_result(field: Tuple[str, ...], result) -> ValueOrError:
    if isinstance(result, Error):
        return attr.evolve(result, field=field + result.field)
    elif not isinstance(result, Value):
        return Value(value=result)
    return result


@attr.frozen
class Field:
    validators: Tuple[Callable, ...]
    """Callable that validate a the given field's value."""

    accepts: Tuple[str]
    """Field names accepted when parsing unvalidated input.

    If left unspecified, effectively defaults to the name of the attribute
    defined on the schema.
    """

    serialize_to: T_Optional[str]
    """If provided overrides the name of the field during seiralialization."""

    serialize_func: T_Optional[Callable]
    """If provided, will be used when serializing this field."""

    nullability: Nullability

    depends_on: Tuple[str, ...]
    """Other fields on the same schema this field depends on"""

    def run_validators(
        self,
        field: Tuple[str, ...],
        value: Any,
        context: Any,
        intermediate_results: Dict[str, Any],
    ) -> Union[Value, Error]:
        def _get_deps(func):
            return {
                param for param in inspect.signature(func).parameters.keys()
            }

        # handle nullability
        if value is omitted and any(
            ['value' in _get_deps(v) for v in self.validators]
        ):
            if isinstance(self.nullability, Required):
                return wrap_result(
                    field=field, result=Error(msg='Value is required.')
                )
            elif isinstance(self.nullability, Optional):
                return Value(self.nullability.omitted_value)
            else:
                raise TypeError

        def inject_deps(func, val):
            deps = _get_deps(func)
            if not deps:
                return func

            if 'context' in deps and context is empty:
                raise ValueError(
                    'Context is required for evaluating this schema.'
                )

            return functools.partial(
                func,
                **{
                    dep: v.value
                    for dep, v in intermediate_results.items()
                    if dep in deps
                },
                **{
                    dep: v
                    for dep, v in {'context': context, 'value': val}.items()
                    if dep in deps
                },
            )

        result = value
        for validator in self.validators:
            result = inject_deps(func=validator, val=result)()
            if isinstance(result, Error):
                return wrap_result(field=field, result=result)

        return wrap_result(field=field, result=result)


def noop(value):
    return value


def field(
    *,
    parents: Tuple[Callable, ...] = tuple(),
    accepts: Tuple[str, ...] = tuple(),
    serialize_to: T_Optional[str] = None,
    serialize_func: Callable = noop,
    nullability: Nullability = Required(),
):
    def _outer_field(inner_func: Callable):
        # find any declared dependencies on other fields
        deps = tuple(
            n
            for n in inspect.signature(inner_func).parameters.keys()
            if n not in {'context', 'value'}
        )

        return Field(
            nullability=nullability,
            validators=parents + (inner_func,),
            accepts=accepts,
            serialize_to=serialize_to,
            serialize_func=serialize_func,
            depends_on=deps,
        )

    return _outer_field


def simple_field(**kwargs):
    """Passthrough to make defining simple fields cleaner."""

    def _simple(value):
        return value

    return field(**kwargs)(_simple)


def getter(dict_or_obj, field, default):
    if isinstance(dict_or_obj, dict):
        return dict_or_obj.get(field, omitted)
    else:
        getattr(dict_or_obj, field, omitted)


SchemaCls = TypeVar('SchemaCls')


def get_fields(cls: SchemaCls) -> Dict[str, Callable]:
    return {
        field_name: field_def
        for field_name, field_def in cls.__dict__.items()
        if isinstance(field_def, Field)
    }


FIELD_TYPE_MAP = {
    int: intfield,
    str: strfield,
}


def schema(cls: SchemaCls, getter=getter, autodef=True):
    """
    Annotate a class to turn it into a schema.

    Args:
        getter: given an object + field name, gets the value from the obj
        autodef: automatically define simple fields for annotated attributes
    """
    # auto define simple annotations
    if autodef:

        def _field_def_from_annotation(annotation):
            if annotation in FIELD_TYPE_MAP:
                return simple_field(parents=(FIELD_TYPE_MAP[annotation],))
            elif typing.get_origin(annotation) is Union:
                # basic support for `Optional`
                union_of = typing.get_args(annotation)
                if not (len(union_of) == 2 and type(None) in union_of):
                    raise TypeError('Unrecognized type annotation.')

                inner = next(
                    t
                    for t in typing.get_args(annotation)
                    if t is not type(None)
                )
                if inner in FIELD_TYPE_MAP:
                    return simple_field(
                        parents=(FIELD_TYPE_MAP[inner],),
                        nullability=Optional(),
                    )

            raise TypeError('Unrecognized type annotation.')

        existing_fields = get_fields(cls)
        for field, f_type in getattr(cls, '__annotations__', {}).items():
            if field not in existing_fields:
                setattr(cls, field, _field_def_from_annotation(f_type))

    # check for dependency loops
    # TODO

    def _clean(data: Any, context: Any) -> Union[SchemaCls, ValidationError]:
        field_defs = [(name, f_def) for name, f_def in get_fields(cls).items()]

        # initial set are those with no
        eval_queue = []
        delayed_eval = []
        for name, f in field_defs:
            if f.depends_on:
                delayed_eval.append((name, f))
            else:
                eval_queue.append((name, f))
        assert len(field_defs) == len(eval_queue) + len(delayed_eval)

        results: Dict[str, Union[Value, Error]] = {}
        while eval_queue:
            field_name, field_def = eval_queue.pop()

            accepts = field_def.accepts or (field_name,)
            for accept in accepts:
                value = getter(data, accept, omitted)
                if value is not omitted:
                    break

            results[field_name] = field_def.run_validators(
                field=(field_name,),
                value=value,
                context=context,
                intermediate_results=results,
            )
            queued_fields = {n for n, _f in eval_queue}
            for name, f in delayed_eval:
                if (
                    name not in results
                    and name not in queued_fields
                    and all([dep in results for dep in f.depends_on])
                ):
                    eval_queue.append((name, f))
        assert {n for n, _f in field_defs} == set(results.keys())

        errors = {f: v for f, v in results.items() if isinstance(v, Error)}
        if errors:
            return ValidationError(errors=list(errors.values()))

        return cls(**results)

    cls.__clean = _clean

    def _new_init(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v.value)

    cls.__init__ = _new_init

    def _serialize(self):
        # very simple serialize
        return {
            field_def.serialize_to
            or field_name: (
                field_def.serialize_func(getattr(self, field_name))
            )
            for field_name, field_def in get_fields(cls).items()
        }

    cls.__serialize = _serialize

    return cls


def clean(
    schema: Type[SchemaCls], data: Any, context: Any = empty
) -> SchemaCls:
    return schema.__clean(data=data, context=context)


def serialize(schema: SchemaCls) -> Dict:
    return schema.__serialize()


@pytest.fixture
def example_schema():
    @schema
    class ExampleSchema:
        myint = simple_field(
            parents=(intfield,), accepts=('myint', 'deprecated_int')
        )

        @field(parents=(intfield,))
        def mylowint(value: int) -> Union[int, Error]:
            if value < 5:
                return value
            else:
                return Error(msg='Needs to be less than 5')

    return ExampleSchema


def test_basic_happy_path(example_schema):
    test_data = {'myint': 100, 'mylowint': 2}
    result = clean(example_schema, test_data)
    assert isinstance(result, example_schema)
    assert result.myint == test_data['myint']
    assert result.mylowint == test_data['mylowint']

    assert test_data == serialize(result)


def test_basic_validation_error(example_schema):
    test_data = {'myint': 100, 'mylowint': 10}
    result = clean(example_schema, test_data)
    assert isinstance(result, ValidationError)
    assert result.errors == [
        Error(msg='Needs to be less than 5', field=('mylowint',))
    ]


def test_accepts(example_schema):
    test_data = {'deprecated_int': 100, 'mylowint': 2}
    result = clean(example_schema, test_data)
    assert isinstance(result, example_schema)
    assert result.myint == test_data['deprecated_int']

    assert serialize(result) == {
        'myint': test_data['deprecated_int'],
        'mylowint': 2,
    }


def test_serialize_to():
    @schema
    class MySchema:
        myint = simple_field(
            parents=(intfield,),
            serialize_to='my_new_int',
        )

    result = clean(MySchema, {'myint': 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert serialize(result) == {'my_new_int': 100}


def test_serialize_func():
    def double(value):
        return value * 2

    @schema
    class MySchema:
        myint = simple_field(
            parents=(intfield,),
            serialize_func=double,
        )

    result = clean(MySchema, {'myint': 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert serialize(result) == {'myint': 200}


def test_autodef():
    @schema
    class MySchema:
        myint: int

    result = clean(MySchema, {'myint': 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert serialize(result) == {'myint': 100}


def test_required():
    @schema
    class MySchema:
        myint: int

    result = clean(MySchema, {})
    assert isinstance(result, ValidationError)
    assert result.errors == [Error(msg='Value is required.', field=('myint',))]


def test_optional():
    @schema
    class MySchema:
        myint: T_Optional[int] = simple_field(
            parents=(intfield,), nullability=Optional(omitted_value=None)
        )

    result = clean(MySchema, {})
    assert isinstance(result, MySchema)
    assert result.myint == None


def test_strfield():
    @schema
    class UserSchema:
        name: str

    result = clean(UserSchema, {'name': 'John'})
    assert isinstance(result, UserSchema)
    assert result.name == 'John'


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
        def organization(value: str, context: Context) -> Organization:
            org = context.org_repo.get_by_pk(value)
            if org:
                return Value(value=org)

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
        result = clean(
            schema=UserSchema,
            data={'name': 'John', 'organization': 'orga_a'},
        )


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


def test_reusable_fields():
    @attr.frozen
    class User:
        pk: str
        name: str
        active: bool = True

    @attr.frozen
    class Organization:
        pk: str
        name: str
        members: List[str]

    @attr.frozen
    class Lead:
        pk: str
        org_id: str
        name: str
        website: str

    billy = User(pk='user_billy', name='Billy')
    joe = User(pk='user_joe', name='Joe')
    charlie = User(pk='user_charlie', name='Charlie')
    dave = User(pk='user_dave', name='Dave', active=False)

    org_a = Organization(
        pk='orga_a',
        name='Organization A',
        members=[billy.pk, dave.pk],
    )
    org_b = Organization(
        pk='orga_b',
        name='Organization B',
        members=[billy.pk, joe.pk],
    )

    ibm = Lead(pk='lead_ibm', name='IBM', website='ibm.com', org_id=org_a.pk)

    class UserRepo:
        USERS_BY_PK = {u.pk: u for u in [billy, joe, charlie]}

        def get_by_pk(self, pk):
            return self.USERS_BY_PK.get(pk, None)

    class OrganizationRepo:
        ORGANIZATIONS_BY_PK = {o.pk: o for o in [org_a, org_b]}

        def get_by_pk(self, pk):
            return self.ORGANIZATIONS_BY_PK.get(pk, None)

    class LeadRepo:
        LEADS_BY_PK = {l.pk: l for l in [ibm]}

        def get_by_pk(self, pk):
            return self.LEADS_BY_PK.get(pk, None)

        def add(self, lead):
            self.LEADS_BY_PK[lead.pk] = lead

    @attr.frozen
    class Context:
        current_user: User
        user_repo: UserRepo
        org_repo: OrganizationRepo
        lead_repo: LeadRepo

    def lookup_org(value: str, context: Context) -> Union[Organization, Error]:
        org = context.org_repo.get_by_pk(value)
        if org:
            return org

        return Error(msg='Organization not found.')

    def validate_org_visibility(
        value: Organization, context: Context
    ) -> Union[Organization, Error]:
        if not context.current_user.active:
            # probably would want to do this when constructing the context
            return Error(msg='User is not active.')

        if context.current_user.pk not in value.members:
            return Error(msg='User cannot access organization.')
        return value

    @schema
    class UpdateLeadRestSchema:
        pk: str
        name: T_Optional[str]
        website: str
        organization: str

    @schema
    class UpdateLead:
        name: Union[str, OMITTED] = simple_field(
            parents=(strfield,), nullability=Optional()
        )
        website: Union[str, OMITTED] = simple_field(
            parents=(strfield,), nullability=Optional()
        )
        organization: Organization = simple_field(
            parents=(lookup_org, validate_org_visibility),
        )

        @field(parents=(strfield,), accepts=('pk',))
        def obj(
            value: str, context: Context, organization: Organization
        ) -> Lead:
            lead = context.lead_repo.get_by_pk(pk=value)
            if lead.org_id != organization.pk:
                return Error(msg='Lead not found.')
            return lead

    # service function
    def update_lead_as_user(pk, name, website, org_id, as_user_id):
        user_repo = UserRepo()
        lead_repo = LeadRepo()
        context = Context(
            current_user=user_repo.get_by_pk(as_user_id),
            org_repo=OrganizationRepo(),
            user_repo=user_repo,
            lead_repo=lead_repo,
        )
        spec = clean(
            schema=UpdateLead,
            data={
                'pk': pk,
                'name': name,
                'website': website,
                'organization': org_id,
            },
            context=context,
        )
        if isinstance(spec, Error):
            raise ValueError(','.join([e.msg for e in spec.errors]))

        changes = {
            field: getattr(spec, field)
            for field in ['name', 'website']
            if getattr(spec, field) is not omitted
        }
        lead = attr.evolve(spec.obj, **changes)
        lead_repo.add(lead)
        return lead

    result = clean(
        schema=UpdateLeadRestSchema,
        data={
            'pk': 'lead_ibm',
            'organization': 'orga_a',
            'website': 'newibm.com',
        },
    )
    assert isinstance(result, UpdateLeadRestSchema)
    assert result.pk == 'lead_ibm'
    assert result.organization == org_a.pk
    assert result.name is omitted
    assert result.website == 'newibm.com'

    new_lead = update_lead_as_user(
        pk=result.pk,
        org_id=result.organization,
        name=result.name,
        website=result.website,
        as_user_id=billy.pk,
    )
    assert new_lead.pk == 'lead_ibm'
    assert new_lead.name == 'IBM'
    assert new_lead.website == 'newibm.com'

    # was actually persisted with the lead repo
    refetched_lead = LeadRepo().get_by_pk(new_lead.pk)
    assert refetched_lead.pk == new_lead.pk
    assert refetched_lead.website == new_lead.website
