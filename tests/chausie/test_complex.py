from typing import List, Union, Optional

import attr

from cleancat.chausie.consts import omitted
from cleancat.chausie.field import Error, simple_field, strfield, field
from cleancat.chausie.schema import schema, clean


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
        name: Optional[str]
        website: str
        organization: str

    @schema
    class UpdateLead:
        name: Optional[str]
        website: Optional[str]
        organization: Organization = simple_field(
            parents=(lookup_org, validate_org_visibility),
        )

        @field(parents=(strfield,), accepts=('pk',))
        def obj(
                value: str, context: Context, organization: Organization
        ) -> Union[Lead, Error]:
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
