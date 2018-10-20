# -*- coding: utf-8 -*-
import datetime
import enum
import re
import unittest

import pytest
from pytz import utc

from cleancat import (
    Bool, Choices, DateTime, Dict, Email, Embedded, Enum, Field, Integer,
    List, Regex, RelaxedURL, Schema, SortedSet, StopValidation, String,
    TrimmedString, URL, ValidationError
)
from cleancat.utils import ValidationTestCase


class TestField:

    def test_it_supports_multiple_base_types(self):
        class IntOrStrField(Field):
            base_type = (int, str)

        assert IntOrStrField().clean(5) == 5
        assert IntOrStrField().clean('five') == 'five'

        with pytest.raises(ValidationError) as e:
            assert IntOrStrField().clean(4.5)
        assert unicode(e.value) == 'Value must be of int or str type.'


class TestStringField:

    def test_it_accepts_valid_input(self):
        value = 'hello world'
        assert String().clean(value) == value

    @pytest.mark.parametrize('value', ['', None])
    def test_it_enforces_the_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            String().clean(value)
        assert unicode(e.value) == 'This field is required.'

    def test_it_accepts_valid_input_if_not_required(self):
        value = 'hello world'
        assert String().clean(value) == value

    @pytest.mark.parametrize('value', ['', None])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            String(required=False).clean(value)
        assert e.value.args[0] == ''

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            String().clean(True)
        assert unicode(e.value) == 'Value must be of basestring type.'

    @pytest.mark.parametrize('value,valid', [
        ('long enough', True),
        ('short', False),
    ])
    def test_it_enforces_min_length(self, value, valid):
        field = String(min_length=10)
        if valid:
            assert field.clean(value) == value
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            assert unicode(e.value) == (
                'The value must be at least 10 characters long.'
            )

    @pytest.mark.parametrize('value,valid', [
        ('short is ok', True),
        ('this is way too long enough', False),
    ])
    def test_it_enforces_max_length(self, value, valid):
        field = String(max_length=12)
        if valid:
            assert field.clean(value) == value
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            assert unicode(e.value) == (
                'The value must be no longer than 12 characters.'
            )

    @pytest.mark.parametrize('value,valid', [
        ('right in the middle', True),
        ('too short', False),
        ('way too long to be valid', False),
    ])
    def test_it_enforces_min_and_max_length(self, value, valid):
        field = String(min_length=10, max_length=20)
        if valid:
            assert field.clean(value) == value
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            assert unicode(e.value) in (
                'The value must be at least 10 characters long.',
                'The value must be no longer than 20 characters.',
            )


class TestTrimmedStringField:

    def test_it_accepts_valid_input(self):
        value = 'hello world'
        assert TrimmedString().clean(value) == value

    @pytest.mark.parametrize('value,expected', [
        ('   hello world    ', 'hello world'),
        ('   hello   world', 'hello   world'),
        ('\rhello\tworld \n', 'hello\tworld'),
    ])
    def test_it_trims_input_surrounded_by_whitespace(self, value, expected):
        assert TrimmedString().clean(value) == expected

    @pytest.mark.parametrize('value', ['', '   ', '\t\n\r', None])
    def test_it_enforces_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            TrimmedString().clean(value)
        assert unicode(e.value) == 'This field is required.'

    @pytest.mark.parametrize('value', ['', '   ', '\t\n\r', None])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            TrimmedString(required=False).clean(value)
        assert e.value.args[0] == ''

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            TrimmedString().clean(True)
        assert unicode(e.value) == 'Value must be of basestring type.'

    @pytest.mark.parametrize('value,expected', [
        ('      valid      ', 'valid'),
        ('        x        ', None),
        ('   way too long  ', None),
    ])
    def test_it_enforces_min_and_max_length(self, value, expected):
        field = TrimmedString(min_length=3, max_length=10)
        if expected:
            assert field.clean(value) == expected
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            assert unicode(e.value) in (
                'The value must be at least 3 characters long.',
                'The value must be no longer than 10 characters.',
            )


class TestBoolField:

    @pytest.mark.parametrize('value', [True, False])
    def test_it_accepts_valid_input(self, value):
        assert Bool().clean(value) == value

    def test_it_enforces_required_flag(self):
        with pytest.raises(ValidationError) as e:
            Bool().clean(None)
        assert unicode(e.value) == 'This field is required.'

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            Bool().clean('')
        assert unicode(e.value) == 'Value must be of bool type.'

    def test_it_can_be_optional(self):
        with pytest.raises(StopValidation) as e:
            Bool(required=False).clean(None)
        # TODO should the blank value for a Bool really be False and not None?
        assert e.value.args[0] is False


class TestRegexField:

    @pytest.mark.parametrize('value', ['a', 'm', 'z'])
    def test_it_accepts_valid_input(self, value):
        assert Regex('^[a-z]$').clean(value) == value

    @pytest.mark.parametrize('value', ['A', 'M', 'Z', 'aa', 'mm', 'zz'])
    def test_it_rejects_invalid_input(self, value):
        with pytest.raises(ValidationError) as e:
            Regex('^[a-z]$').clean(value)
        assert unicode(e.value) == 'Invalid input.'

    @pytest.mark.parametrize('value', ['A', 'M', 'Z'])
    def test_it_accepts_case_insensitive_input(self, value):
        assert Regex('^[a-z]$', re.IGNORECASE).clean(value) == value

    def test_it_supports_custom_error_messaging(self):
        err_msg = 'Not a lowercase letter.'
        with pytest.raises(ValidationError) as e:
            Regex('^[a-z]$', regex_message=err_msg).clean('aa')
        assert unicode(e.value) == err_msg

    @pytest.mark.parametrize('value', ['', None])
    def test_it_enforces_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            Regex('^[a-z]$').clean(value)
        assert unicode(e.value) == 'This field is required.'

    @pytest.mark.parametrize('value', ['', None])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            Regex('^[a-z]$', required=False).clean(value)
        assert e.value.args[0] == ''

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            Regex('^[a-z]$').clean(True)
        assert unicode(e.value) == 'Value must be of basestring type.'


class TestDateTimeField:

    def test_it_accepts_date_string(self):
        assert DateTime().clean('2012-10-09') == datetime.date(2012, 10, 9)

    def test_it_accepts_datetime_string(self):
        expected = datetime.datetime(2012, 10, 9, 13, 10, 4)
        assert DateTime().clean('2012-10-09 13:10:04') == expected

    def test_it_supports_tzinfo(self):
        raw = '2013-03-27T01:02:01.137000+00:00'
        expected = datetime.datetime(2013, 3, 27, 1, 2, 1, 137000, tzinfo=utc)
        assert DateTime().clean(raw) == expected

    def test_it_rejects_invalid_year_range(self):
        with pytest.raises(ValidationError) as e:
            DateTime().clean('0000-01-01T00:00:00-08:00')
        assert unicode(e.value) == 'Could not parse date: year is out of range'

    @pytest.mark.parametrize('value', [
        '2012a', 'alksdjf', '111111111'
    ])
    def test_it_rejects_invalid_dates(self, value):
        with pytest.raises(ValidationError) as e:
            DateTime().clean(value)
        assert unicode(e.value) == 'Invalid ISO 8601 datetime.'

    @pytest.mark.parametrize('value', ['', None])
    def test_it_enforces_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            DateTime().clean(value)
        assert unicode(e.value) == 'This field is required.'

    @pytest.mark.parametrize('value', ['', None])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            DateTime(required=False).clean(value)
        assert e.value.args[0] is None

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            DateTime().clean(True)
        assert unicode(e.value) == 'Value must be of basestring type.'


class TestEmailField:

    def test_it_accepts_valid_email_addresses(self):
        value = 'test@example.com'
        assert Email().clean(value) == value

    @pytest.mark.parametrize('value', [
        'test@example',
        'test.example.com',
    ])
    def test_it_rejects_invalid_email_addresses(self, value):
        with pytest.raises(ValidationError) as e:
            Email().clean(value)
        assert unicode(e.value) == 'Invalid email address.'

    def test_it_autotrims_input(self):
        assert Email().clean('   test@example.com   ') == 'test@example.com'

    @pytest.mark.parametrize('value, valid', [
        ('{u}@{d}.{d}.{d}.example'.format(u='u' * 54, d='d' * 63), True),

        # Emails must not be longer than 254 characters.
        ('{u}@{d}.{d}.{d}.example'.format(u='u' * 55, d='d' * 63), False),
    ])
    def test_it_enforces_max_email_address_length(self, value, valid):
        field = Email()
        if valid:
            assert field.clean(value) == value
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            err_msg = 'The value must be no longer than 254 characters.'
            assert unicode(e.value) == err_msg

    @pytest.mark.parametrize('value', ['', None])
    def test_it_enforces_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            Email().clean(value)
        assert unicode(e.value) == 'This field is required.'

    @pytest.mark.parametrize('value', ['', None])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            Email(required=False).clean(value)
        assert e.value.args[0] == ''

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            Email().clean(True)
        assert unicode(e.value) == 'Value must be of basestring type.'


class TestIntegerField:

    @pytest.mark.parametrize('value', [-1, 0, 100, 1000000])
    def test_it_accepts_valid_integers(self, value):
        assert Integer().clean(value) == value

    @pytest.mark.parametrize('value, valid', [
        (10, True),
        (0, True),
        (-1, False),
    ])
    def test_it_enforces_min_value(self, value, valid):
        field = Integer(min_value=0)
        if valid:
            assert field.clean(value) == value
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            assert unicode(e.value) == 'The value must be at least 0.'

    @pytest.mark.parametrize('value, valid', [
        (-1, True),
        (0, True),
        (100, True),
        (101, False),
    ])
    def test_it_enforces_max_value(self, value, valid):
        field = Integer(max_value=100)
        if valid:
            assert field.clean(value) == value
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            assert unicode(e.value) == 'The value must not be larger than 100.'

    @pytest.mark.parametrize('value, valid', [
        (-1, False),
        (0, True),
        (50, True),
        (100, True),
        (101, False),
    ])
    def test_it_enforces_min_and_max_value(self, value, valid):
        field = Integer(min_value=0, max_value=100)
        if valid:
            assert field.clean(value) == value
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            assert unicode(e.value) in (
                'The value must be at least 0.',
                'The value must not be larger than 100.',
            )

    def test_it_enforces_required_flag(self):
        with pytest.raises(ValidationError) as e:
            Integer().clean(None)
        assert unicode(e.value) == 'This field is required.'

    def test_it_can_be_optional(self):
        with pytest.raises(StopValidation) as e:
            Integer(required=False).clean(None)
        assert e.value.args[0] is None

    @pytest.mark.parametrize('value', ['', '0', 23.0])
    def test_it_enforces_valid_data_type(self, value):
        with pytest.raises(ValidationError) as e:
            Integer().clean(value)
        assert unicode(e.value) == 'Value must be of int type.'


class TestListField:

    def test_it_accepts_a_list_of_values(self):
        values = ['a', 'b', 'c']
        assert List(String()).clean(values) == values

    def test_it_validates_each_value(self):
        with pytest.raises(ValidationError) as e:
            List(String(max_length=3)).clean(['a', 2, 'c', 'long'])
        assert e.value.args[0] == {
            'errors': {
                1: 'Value must be of basestring type.',
                3: 'The value must be no longer than 3 characters.',
            }
        }

    @pytest.mark.parametrize('value, valid', [
        (['a', 'b'], True),
        (['a', 'b', 'c'], True),
        (['a', 'b', 'c', 'd'], False),
    ])
    def test_it_enforces_max_length(self, value, valid):
        field = List(String(), max_length=3)
        if valid:
            assert field.clean(value) == value
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            assert unicode(e.value) == 'List is too long.'

    @pytest.mark.parametrize('value', [None, []])
    def test_it_enforces_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            List(String()).clean(value)
        assert unicode(e.value) == 'This field is required.'

    @pytest.mark.parametrize('value', [None, []])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            List(String(), required=False).clean(value)
        assert e.value.args[0] == []


class TestSortedSetField:

    def test_it_dedupes_valid_values(self):
        assert SortedSet(String()).clean(['a', 'b', 'a']) == ['a', 'b']

    def test_it_sorts_valid_values(self):
        assert SortedSet(String()).clean(['b', 'a']) == ['a', 'b']

    def test_it_enforces_required_flag(self):
        with pytest.raises(ValidationError) as e:
            SortedSet(String()).clean(None)
        assert unicode(e.value) == 'This field is required.'

    def test_it_can_be_optional(self):
        with pytest.raises(StopValidation) as e:
            SortedSet(String(), required=False).clean(None)
        assert e.value.args[0] == []

    @pytest.mark.parametrize('value', [23.0, True])
    def test_it_enforces_valid_data_type(self, value):
        with pytest.raises(ValidationError) as e:
            SortedSet(String()).clean(value)
        assert unicode(e.value) == 'Value must be of list type.'


# TODO for schema-level tests: test empty dict
# TODO for schema-level tests: test blank values beyond StopValidation
# TODO for schema-level tests: test no new data and orig_data keeps old values


class FieldTestCase(ValidationTestCase):

    def test_choice(self):
        class ChoiceSchema(Schema):
            choice = Choices(choices=['Hello', 'world'])

        self.assertValid(ChoiceSchema({'choice': 'Hello'}), {'choice': 'Hello'})
        self.assertInvalid(ChoiceSchema({'choice': 'World'}), {'field-errors': ['choice']})
        self.assertInvalid(ChoiceSchema({'choice': 'invalid'}), {'field-errors': ['choice']})

        class CaseInsensitiveChoiceSchema(Schema):
            choice = Choices(choices=['Hello', 'world'], case_insensitive=True)

        self.assertValid(CaseInsensitiveChoiceSchema({'choice': 'Hello'}), {'choice': 'Hello'})
        self.assertValid(CaseInsensitiveChoiceSchema({'choice': 'hello'}), {'choice': 'Hello'})
        self.assertValid(CaseInsensitiveChoiceSchema({'choice': 'wOrLd'}), {'choice': 'world'})
        self.assertInvalid(CaseInsensitiveChoiceSchema({'choice': 'world '}), {'field-errors': ['choice']})
        self.assertInvalid(CaseInsensitiveChoiceSchema({'choice': 'invalid'}), {'field-errors': ['choice']})

    def test_enum(self):
        class MyChoices(enum.Enum):
            A = 'a'
            B = 'b'

        class ChoiceSchema(Schema):
            choice = Enum(MyChoices)

        self.assertValid(ChoiceSchema({'choice': 'a'}), {'choice': MyChoices.A})
        self.assertValid(ChoiceSchema({'choice': 'b'}), {'choice': MyChoices.B})
        self.assertInvalid(ChoiceSchema({'choice': 'c'}), {'field-errors': ['choice']})

    def test_enum_with_choices(self):
        class MyChoices(enum.Enum):
            A = 'a'
            B = 'b'
            C = 'c'

        class ChoiceSchema(Schema):
            choice = Enum([MyChoices.A, MyChoices.B])

        self.assertValid(ChoiceSchema({'choice': 'a'}), {'choice': MyChoices.A})
        self.assertValid(ChoiceSchema({'choice': 'b'}), {'choice': MyChoices.B})
        self.assertInvalid(ChoiceSchema({'choice': 'c'}), {'field-errors': ['choice']})

    def test_url(self):
        class URLSchema(Schema):
            url = URL()

        self.assertValid(URLSchema({'url': 'http://x.com'}), {'url': 'http://x.com'})
        self.assertValid(URLSchema({'url': u'http://♡.com'}), {'url': u'http://♡.com'})
        self.assertValid(URLSchema({'url': 'http://example.com/a?b=c'}), {'url': 'http://example.com/a?b=c'})
        self.assertValid(URLSchema({'url': 'ftp://ftp.example.com'}), {'url': 'ftp://ftp.example.com'})
        self.assertValid(URLSchema({'url': 'http://example.com?params=without&path'}), {'url': 'http://example.com?params=without&path'})
        self.assertInvalid(URLSchema({'url': 'www.example.com'}), {'field-errors': ['url']})
        self.assertInvalid(URLSchema({'url': 'http:// invalid.com'}), {'field-errors': ['url']})
        self.assertInvalid(URLSchema({'url': 'http://!nvalid.com'}), {'field-errors': ['url']})
        self.assertInvalid(URLSchema({'url': 'http://.com'}), {'field-errors': ['url']})
        self.assertInvalid(URLSchema({'url': 'http://'}), {'field-errors': ['url']})
        self.assertInvalid(URLSchema({'url': 'http://.'}), {'field-errors': ['url']})
        self.assertInvalid(URLSchema({'url': 'invalid'}), {'field-errors': ['url']})

        # full-width chars disallowed
        self.assertInvalid(URLSchema({'url': u'http://ＧＯＯＧＬＥ.com'}), {'field-errors': ['url']})

        # Russian unicode URL (IDN, unicode path and query params)
        self.assertValid(URLSchema({'url': u'http://пример.com'}), {'url': u'http://пример.com'})
        self.assertValid(URLSchema({'url': u'http://пример.рф'}), {'url': u'http://пример.рф'})
        self.assertValid(URLSchema({'url': u'http://пример.рф/путь/?параметр=значение'}), {'url': u'http://пример.рф/путь/?параметр=значение'})

        # Punicode stuff
        self.assertValid(URLSchema({'url': u'http://test.XN--11B4C3D'}), {'url': u'http://test.XN--11B4C3D'})

        # http://stackoverflow.com/questions/9238640/how-long-can-a-tld-possibly-be
        # Longest to date (Feb 2017) TLD in punicode format is 24 chars long
        self.assertValid(URLSchema({'url': u'http://test.xn--vermgensberatung-pwb'}), {'url': u'http://test.xn--vermgensberatung-pwb'})

    def test_url_required_flag(self):
        class URLSchema(Schema):
            url = URL()

        for value in (None, ''):
            schema = URLSchema({'url': value})
            self.assertInvalid(schema, {'field-errors': ['url']})
            assert schema.field_errors['url'] == 'This field is required.'

    def test_url_bad_data_type(self):
        class URLSchema(Schema):
            url = URL()

        schema = URLSchema({'url': 23.0})
        self.assertInvalid(schema, {'field-errors': ['url']})
        assert schema.field_errors['url'] == 'Value must be of basestring type.'

    def test_url_with_default_schema(self):
        class DefaultURLSchema(Schema):
            url = URL(default_scheme='http://')

        self.assertValid(DefaultURLSchema({'url': 'http://example.com/a?b=c'}), {'url': 'http://example.com/a?b=c'})
        self.assertValid(DefaultURLSchema({'url': 'ftp://ftp.example.com'}), {'url': 'ftp://ftp.example.com'})
        self.assertValid(DefaultURLSchema({'url': 'www.example.com'}), {'url': 'http://www.example.com'})
        self.assertInvalid(DefaultURLSchema({'url': 'invalid'}), {'field-errors': ['url']})
        self.assertInvalid(DefaultURLSchema({'url': True}), {'field-errors': ['url']})

    def test_relaxed_url(self):
        class RelaxedURLSchema(Schema):
            url = RelaxedURL(default_scheme='http://')

        self.assertValid(RelaxedURLSchema({'url': 'http://example.com/a?b=c'}), {'url': 'http://example.com/a?b=c'})
        self.assertValid(RelaxedURLSchema({'url': 'ftp://ftp.example.com'}), {'url': 'ftp://ftp.example.com'})
        self.assertValid(RelaxedURLSchema({'url': 'www.example.com'}), {'url': 'http://www.example.com'})
        self.assertValid(RelaxedURLSchema({'url': u'http://пример.рф'}), {'url': u'http://пример.рф'})
        self.assertInvalid(RelaxedURLSchema({'url': 'http:// invalid.com'}), {'field-errors': ['url']})
        self.assertInvalid(RelaxedURLSchema({'url': 'http://!nvalid.com'}), {'field-errors': ['url']})
        self.assertInvalid(RelaxedURLSchema({'url': 'http://'}), {'field-errors': ['url']})
        self.assertInvalid(RelaxedURLSchema({'url': 'invalid'}), {'field-errors': ['url']})
        self.assertInvalid(RelaxedURLSchema({'url': True}), {'field-errors': ['url']})

    def test_optional_relaxed_url(self):
        class OptionalRelaxedURLSchema(Schema):
            url = RelaxedURL(required=False, default_scheme='http://')

        self.assertValid(OptionalRelaxedURLSchema({'url': 'http://example.com/a?b=c'}), {'url': 'http://example.com/a?b=c'})
        self.assertValid(OptionalRelaxedURLSchema({'url': 'ftp://ftp.example.com'}), {'url': 'ftp://ftp.example.com'})
        self.assertValid(OptionalRelaxedURLSchema({'url': 'www.example.com'}), {'url': 'http://www.example.com'})
        self.assertValid(OptionalRelaxedURLSchema({'url': 'http://'}), {'url': None})
        self.assertInvalid(OptionalRelaxedURLSchema({'url': 'invalid'}), {'field-errors': ['url']})
        self.assertInvalid(OptionalRelaxedURLSchema({'url': True}), {'field-errors': ['url']})

    def test_url_with_allowed_schemes(self):
        class OnlyHTTPSURLSchema(Schema):
            url = URL(default_scheme='https://', allowed_schemes=['https://'])

        self.assertValid(OnlyHTTPSURLSchema({'url': 'https://example.com/'}), {'url': 'https://example.com/'})
        self.assertValid(OnlyHTTPSURLSchema({'url': 'example.com/'}), {'url': 'https://example.com/'})
        self.assertInvalid(OnlyHTTPSURLSchema({'url': 'http://example.com'}), {'field-errors': ['url']})
        self.assertInvalid(OnlyHTTPSURLSchema({'url': True}), {'field-errors': ['url']})

        class ShortSchemeURLSchema(Schema):
            url = URL(default_scheme='https', allowed_schemes=['https', 'ftps'])

        self.assertValid(ShortSchemeURLSchema({'url': 'https://example.com/'}), {'url': 'https://example.com/'})
        self.assertValid(ShortSchemeURLSchema({'url': 'example.com/'}), {'url': 'https://example.com/'})
        self.assertValid(ShortSchemeURLSchema({'url': 'ftps://storage.example.com/'}), {'url': 'ftps://storage.example.com/'})
        self.assertInvalid(ShortSchemeURLSchema({'url': 'http://example.com'}), {'field-errors': ['url']})
        self.assertInvalid(ShortSchemeURLSchema({'url': True}), {'field-errors': ['url']})

    def test_embedded(self):
        class UserSchema(Schema):
            email = Email()

        class MemberSchema(Schema):
            user = Embedded(UserSchema)

        self.assertValid(MemberSchema({
            'user': {'email': 'a@example.com'}
        }), {
            'user': {'email': 'a@example.com'}
        })

        self.assertInvalid(MemberSchema({
            'user': {'email': 'invalid'}
        }), error_obj={
            'field-errors': {
                'user': {
                    'errors': [],
                    'field-errors': {
                        'email': 'Invalid email address.'
                    }
                }
            }
        })

        self.assertInvalid(MemberSchema({
            'user': {}
        }), error_obj={
            'field-errors': {
                'user': 'This field is required.'
            }
        })

    def test_mutable(self):
        class UnmutableSchema(Schema):
            text = String(mutable=False)

        self.assertValid(UnmutableSchema({'text': 'hello'}), {'text': 'hello'})
        self.assertInvalid(UnmutableSchema({'text': 'hello'}, {'text': 'existing'}), {'field-errors': ['text']})
        self.assertInvalid(UnmutableSchema({'text': 'hello'}, {'text': ''}), {'field-errors': ['text']})
        self.assertInvalid(UnmutableSchema({'text': 'hello'}, {'text': None}), {'field-errors': ['text']})
        self.assertInvalid(UnmutableSchema({'text': ''}, {'text': 'existing'}), {'field-errors': ['text']})
        self.assertInvalid(UnmutableSchema({'text': None}, {'text': 'existing'}), {'field-errors': ['text']})
        self.assertValid(UnmutableSchema({'text': 'existing'}, {'text': 'existing'}), {'text': 'existing'})
        self.assertValid(UnmutableSchema({}, {'text': 'hello'}), {'text': 'hello'})
        self.assertValid(UnmutableSchema({'text': 'hello'}, {}), {'text': 'hello'})


class ExternalCleanTestCase(unittest.TestCase):
    """
    Collection of tests making sure Schema#external_clean works as
    expected.
    """

    def setUp(self):

        # Generic message schema that may be used in composition with more
        # specific schemas
        class MessageSchema(Schema):
            status = String(required=True)

            def clean(self):
                orig_status = self.orig_data and self.orig_data['status']
                new_status = self.data['status']

                if (orig_status == 'sent' and new_status == 'inbox'):
                    self.field_errors['status'] = "Can't change from sent to inbox"

                self.data['message_cleaned'] = True

                return self.data

        # Specific email schema that also calls the generic message schema
        # via external_clean
        class EmailSchema(Schema):
            subject = String()

            def full_clean(self):
                super(EmailSchema, self).full_clean()
                self.external_clean(MessageSchema)

        self.MessageSchema = MessageSchema
        self.EmailSchema = EmailSchema

    def test_external_clean(self):
        schema = self.EmailSchema(
            raw_data={'subject': 'hi', 'status': 'sent'},
        )
        schema.full_clean()
        assert schema.data == {
            'subject': 'hi',
            'status': 'sent',
            'message_cleaned': True,
        }

    def test_orig_data_in_external_clean(self):

        # Create a schema for an existing object, which originally had
        # subject='hi' and status='sent' and we're trying to validate an
        # update to subject='hi updated' and status='inbox' (which shouldn't
        # be allowed).
        schema = self.EmailSchema(
            raw_data={'subject': 'hi updated', 'status': 'inbox'},
            data={'subject': 'hi', 'status': 'sent'},
        )

        with pytest.raises(ValidationError):
            schema.full_clean()

        assert schema.field_errors == {
            'status': "Can't change from sent to inbox"
        }


class TestSchema:

    def test_serialization(self):
        class EmbeddedSchema(Schema):
            date_time = DateTime()

        class TestSchema(Schema):
            string = String()
            boolean = Bool()
            date_time = DateTime()
            integer = Integer()
            lst = List(DateTime())
            embedded = Embedded(EmbeddedSchema)

        schema = TestSchema(data={
            'string': 'foo',
            'boolean': True,
            'date_time': datetime.datetime(2016, 1, 2, 3, 4, 5),
            'integer': 1234,
            'lst': [datetime.datetime(2016, 1, 2, 3, 4, 5),
                    datetime.datetime(2016, 1, 3)],
            'embedded': {'date_time': datetime.datetime(2000, 1, 1)},
        })

        serialized = schema.serialize()
        assert serialized == {
            'string': 'foo',
            'boolean': True,
            'date_time': '2016-01-02T03:04:05',
            'integer': 1234,
            'lst': ['2016-01-02T03:04:05', '2016-01-03T00:00:00'],
            'embedded': {'date_time': '2000-01-01T00:00:00'},
        }

    def test_serialization_optional_fields(self):
        class EmbeddedSchema(Schema):
            date_time = DateTime()

        class TestSchema(Schema):
            name = String(required=True)
            string = String(required=False)
            choice = Choices(['a', 'b'], required=False)
            boolean = Bool(required=False)
            date_time = DateTime(required=False)
            integer = Integer(required=False)
            embedded = Embedded(EmbeddedSchema, required=False)
            lst = List(DateTime(), required=False)
            sorted_set = SortedSet(String(), required=False)
            dictionary = Dict(required=False)

        schema = TestSchema(data={
            'name': 'One Required Field',
            'string': None,
            'choice': None,
            'boolean': None,
            'date_time': None,
            'integer': None,
            'embedded': None,
            'lst': None,
            'sorted_set': None,
            'dictionary': None,
        })
        serialized = schema.serialize()
        assert serialized == {
            'name': 'One Required Field',
            'string': None,
            'choice': None,
            'boolean': None,
            'date_time': None,
            'integer': None,
            'embedded': None,
            'lst': [],
            'sorted_set': [],
            'dictionary': {},
        }

    def test_serialization_enum(self):
        class MyChoices(enum.Enum):
            A = 'a'
            B = 'b'

        class TestSchema(Schema):
            enum = Enum(MyChoices)
            optional_enum = Enum(MyChoices, required=False)
            lst = List(Enum(MyChoices))

        schema = TestSchema(data={
            'enum': MyChoices.A,
            'optional_enum': None,
            'lst': [MyChoices.A, MyChoices.B],
        })

        serialized = schema.serialize()
        assert serialized == {
            'enum': 'a',
            'optional_enum': None,
            'lst': ['a', 'b'],
        }

    def test_raw_field_name_serialization(self):
        class TestSchema(Schema):
            value = String(raw_field_name='value_id')

        schema = TestSchema(raw_data={'value_id': 'val_xyz'})

        schema.full_clean()
        assert schema.data == {'value': 'val_xyz'}

        serialized = schema.serialize()
        assert serialized == {'value_id': 'val_xyz'}

    def test_raw_field_name_error(self):
        class TestSchema(Schema):
            value = Integer(raw_field_name='value_id')

        schema = TestSchema(raw_data={'value_id': 'not-an-integer'})

        with pytest.raises(ValidationError):
            schema.full_clean()

        assert schema.field_errors == {
            'value_id': 'Value must be of int type.'
        }
