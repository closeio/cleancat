# -*- coding: utf-8 -*-
import datetime
import enum
import re

import pytest
from pytz import utc

from cleancat import (
    Bool, Choices, DateTime, Dict, Email, Embedded, Enum, Field, Integer,
    List, Regex, RelaxedURL, Schema, SortedSet, StopValidation, String,
    TrimmedString, URL, ValidationError
)


class TestField:

    def test_it_supports_multiple_base_types(self):
        class IntOrStrField(Field):
            base_type = (int, str)

        assert IntOrStrField().clean(5) == 5
        assert IntOrStrField().clean('five') == 'five'

        with pytest.raises(ValidationError) as e:
            assert IntOrStrField().clean(4.5)
        assert e.value.args[0] == 'Value must be of int or str type.'


class TestStringField:

    def test_it_accepts_valid_input(self):
        value = 'hello world'
        assert String().clean(value) == value

    @pytest.mark.parametrize('value', ['', None])
    def test_it_enforces_the_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            String().clean(value)
        assert e.value.args[0] == 'This field is required.'

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
        assert e.value.args[0] in (
            # TODO this should be consistent and say the same thing for both.
            'Value must be of basestring type.',  # Py2
            'Value must be of str type.',  # Py3
        )

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
            assert e.value.args[0] == (
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
            assert e.value.args[0] == (
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
            assert e.value.args[0] in (
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
        assert e.value.args[0] == 'This field is required.'

    @pytest.mark.parametrize('value', ['', '   ', '\t\n\r', None])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            TrimmedString(required=False).clean(value)
        assert e.value.args[0] == ''

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            TrimmedString().clean(True)
        assert e.value.args[0] in (
            'Value must be of basestring type.',
            'Value must be of str type.',
        )

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
            assert e.value.args[0] in (
                'The value must be at least 3 characters long.',
                'The value must be no longer than 10 characters.',
            )


class TestChoicesField:

    @pytest.mark.parametrize('value', ['Hello', 'World'])
    def test_it_accepts_valid_choices(self, value):
        assert Choices(choices=['Hello', 'World']).clean(value) == value

    @pytest.mark.parametrize('value', ['hello', 'Invalid'])
    def test_it_rejects_invalid_choices(self, value):
        with pytest.raises(ValidationError) as e:
            Choices(choices=['Hello', 'World']).clean(value)
        assert e.value.args[0] == 'Not a valid choice.'

    def test_it_supports_case_insensitiveness(self):
        field = Choices(choices=['Hello', 'WORLD'], case_insensitive=True)
        assert field.clean('HeLlO') == 'Hello'
        assert field.clean('woRlD') == 'WORLD'


class TestBoolField:

    @pytest.mark.parametrize('value', [True, False])
    def test_it_accepts_valid_input(self, value):
        assert Bool().clean(value) == value

    def test_it_enforces_required_flag(self):
        with pytest.raises(ValidationError) as e:
            Bool().clean(None)
        assert e.value.args[0] == 'This field is required.'

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            Bool().clean('')
        assert e.value.args[0] == 'Value must be of bool type.'

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
        assert e.value.args[0] == 'Invalid input.'

    @pytest.mark.parametrize('value', ['A', 'M', 'Z'])
    def test_it_accepts_case_insensitive_input(self, value):
        assert Regex('^[a-z]$', re.IGNORECASE).clean(value) == value

    def test_it_supports_custom_error_messaging(self):
        err_msg = 'Not a lowercase letter.'
        with pytest.raises(ValidationError) as e:
            Regex('^[a-z]$', regex_message=err_msg).clean('aa')
        assert e.value.args[0] == err_msg

    @pytest.mark.parametrize('value', ['', None])
    def test_it_enforces_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            Regex('^[a-z]$').clean(value)
        assert e.value.args[0] == 'This field is required.'

    @pytest.mark.parametrize('value', ['', None])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            Regex('^[a-z]$', required=False).clean(value)
        assert e.value.args[0] == ''

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            Regex('^[a-z]$').clean(True)
        assert e.value.args[0] in (
            'Value must be of basestring type.',
            'Value must be of str type.',
        )


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
        assert e.value.args[0] in (
            # TODO this should be consistent and say the same thing for both.
            'Could not parse date: year is out of range',  # Py2
            'Could not parse date: year 0 is out of range',  # Py3
        )

    @pytest.mark.parametrize('value', [
        '2012a', 'alksdjf', '111111111'
    ])
    def test_it_rejects_invalid_dates(self, value):
        with pytest.raises(ValidationError) as e:
            DateTime().clean(value)
        assert e.value.args[0] == 'Invalid ISO 8601 datetime.'

    @pytest.mark.parametrize('value', ['', None])
    def test_it_enforces_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            DateTime().clean(value)
        assert e.value.args[0] == 'This field is required.'

    @pytest.mark.parametrize('value', ['', None])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            DateTime(required=False).clean(value)
        assert e.value.args[0] is None

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            DateTime().clean(True)
        assert e.value.args[0] in (
            'Value must be of basestring type.',
            'Value must be of str type.',
        )


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
        assert e.value.args[0] == 'Invalid email address.'

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
            assert e.value.args[0] == err_msg

    @pytest.mark.parametrize('value', ['', None])
    def test_it_enforces_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            Email().clean(value)
        assert e.value.args[0] == 'This field is required.'

    @pytest.mark.parametrize('value', ['', None])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            Email(required=False).clean(value)
        assert e.value.args[0] == ''

    def test_it_enforces_valid_data_type(self):
        with pytest.raises(ValidationError) as e:
            Email().clean(True)
        assert e.value.args[0] in (
            'Value must be of basestring type.',
            'Value must be of str type.',
        )


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
            assert e.value.args[0] == 'The value must be at least 0.'

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
            assert e.value.args[0] == 'The value must not be larger than 100.'

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
            assert e.value.args[0] in (
                'The value must be at least 0.',
                'The value must not be larger than 100.',
            )

    def test_it_enforces_required_flag(self):
        with pytest.raises(ValidationError) as e:
            Integer().clean(None)
        assert e.value.args[0] == 'This field is required.'

    def test_it_can_be_optional(self):
        with pytest.raises(StopValidation) as e:
            Integer(required=False).clean(None)
        assert e.value.args[0] is None

    @pytest.mark.parametrize('value', ['', '0', 23.0])
    def test_it_enforces_valid_data_type(self, value):
        with pytest.raises(ValidationError) as e:
            Integer().clean(value)
        assert e.value.args[0] == 'Value must be of int type.'


class TestListField:

    def test_it_accepts_a_list_of_values(self):
        values = ['a', 'b', 'c']
        assert List(String()).clean(values) == values

    def test_it_validates_each_value(self):
        with pytest.raises(ValidationError) as e:
            List(String(max_length=3)).clean(['a', 2, 'c', 'long'])
        assert e.value.args[0]['errors'][1] in (
            'Value must be of basestring type.',
            'Value must be of str type.',
        )
        assert e.value.args[0]['errors'][3] == (
            'The value must be no longer than 3 characters.'
        )

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
            assert e.value.args[0] == 'List is too long.'

    @pytest.mark.parametrize('value', [None, []])
    def test_it_enforces_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            List(String()).clean(value)
        assert e.value.args[0] == 'This field is required.'

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
        assert e.value.args[0] == 'This field is required.'

    def test_it_can_be_optional(self):
        with pytest.raises(StopValidation) as e:
            SortedSet(String(), required=False).clean(None)
        assert e.value.args[0] == []

    @pytest.mark.parametrize('value', [23.0, True])
    def test_it_enforces_valid_data_type(self, value):
        with pytest.raises(ValidationError) as e:
            SortedSet(String()).clean(value)
        assert e.value.args[0] == 'Value must be of list type.'


class TestEnumField:

    @pytest.fixture
    def enum_cls(self):
        class MyChoices(enum.Enum):
            A = 'a'
            B = 'b'
            C = 'c'

        return MyChoices

    def test_it_accepts_valid_choices(self, enum_cls):
        assert Enum(enum_cls).clean('a') == enum_cls.A
        assert Enum(enum_cls).clean('b') == enum_cls.B
        assert Enum(enum_cls).clean('c') == enum_cls.C

    def test_it_rejects_invalid_choices(self, enum_cls):
        with pytest.raises(ValidationError) as e:
            Enum(enum_cls).clean('d')
        assert e.value.args[0] == 'Not a valid choice.'

    def test_it_accepts_a_sublist_of_choices(self, enum_cls):
        field = Enum([enum_cls.A, enum_cls.B])
        assert field.clean('a') == enum_cls.A
        assert field.clean('b') == enum_cls.B
        with pytest.raises(ValidationError) as e:
            field.clean('c')
        assert e.value.args[0] == 'Not a valid choice.'


class TestURLField:

    @pytest.mark.parametrize('value', [
        'http://x.com',
        u'http://♡.com',
        'http://example.com/a?b=c',
        'ftp://ftp.example.com',
        'http://example.com?params=without&path',

        # Russian unicode URL (IDN, unicode path and query params)
        u'http://пример.com',
        u'http://пример.рф',
        u'http://пример.рф/путь/?параметр=значение',

        # Punicode stuff
        u'http://test.XN--11B4C3D',

        # http://stackoverflow.com/questions/9238640/how-long-can-a-tld-possibly-be
        # Longest to date (Feb 2017) TLD in punicode format is 24 chars long
        u'http://test.xn--vermgensberatung-pwb',
    ])
    def test_in_accepts_valid_urls(self, value):
        assert URL().clean(value) == value

    @pytest.mark.parametrize('value', [
        'www.example.com',
        'http:// invalid.com',
        'http://!nvalid.com',
        'http://.com',
        'http://',
        'http://.',
        'invalid',
        u'http://ＧＯＯＧＬＥ.com',  # full-width chars are disallowed
    ])
    def test_it_rejects_invalid_urls(self, value):
        with pytest.raises(ValidationError) as e:
            URL().clean(value)
        assert e.value.args[0] == 'Invalid URL.'

    @pytest.mark.parametrize('value, expected', [
        ('http://example.com/a?b=c', 'http://example.com/a?b=c'),
        ('ftp://ftp.example.com', 'ftp://ftp.example.com'),
        ('www.example.com', 'http://www.example.com'),
        ('invalid', None),
        (True, None),
    ])
    def test_it_supports_a_default_scheme(self, value, expected):
        field = URL(default_scheme='http://')
        if expected:
            assert field.clean(value) == expected
        else:
            pytest.raises(ValidationError, field.clean, value)

    @pytest.mark.parametrize('value, expected', [
        ('https://example.com/', 'https://example.com/'),
        ('example.com/', 'https://example.com/'),
        ('http://example.com', None),
    ])
    def test_it_enforces_allowed_schemes(self, value, expected):
        field = URL(default_scheme='https://', allowed_schemes=['https://'])
        if expected:
            assert field.clean(value) == expected
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            assert e.value.args[0] == (
                "This URL uses a scheme that's not allowed. You can only "
                "use https://."
            )

    @pytest.mark.parametrize('value, expected', [
        ('https://example.com/', 'https://example.com/'),
        ('example.com/', 'https://example.com/'),
        ('ftps://storage.example.com', 'ftps://storage.example.com'),
    ])
    def test_it_supports_simpler_allowed_scheme_values(self, value, expected):
        field = URL(default_scheme='https', allowed_schemes=['https', 'ftps'])
        assert field.clean(value) == expected

    @pytest.mark.parametrize('value', ['', None])
    def test_it_enforces_required_flag(self, value):
        with pytest.raises(ValidationError) as e:
            URL().clean(value)
        assert e.value.args[0] == 'This field is required.'

    @pytest.mark.parametrize('value', ['', None])
    def test_it_can_be_optional(self, value):
        with pytest.raises(StopValidation) as e:
            URL(required=False).clean(value)
        assert e.value.args[0] is None

    @pytest.mark.parametrize('value', [23.0, True])
    def test_it_enforces_valid_data_type(self, value):
        with pytest.raises(ValidationError) as e:
            URL().clean(value)
        assert e.value.args[0] in (
            'Value must be of basestring type.',
            'Value must be of str type.',
        )


class TestRelaxedURLField:

    @pytest.mark.parametrize('value', [
        'http://example.com/a?b=c',
        'ftp://ftp.example.com',
        u'http://пример.рф',
    ])
    def test_it_accepts_valid_urls(self, value):
        RelaxedURL().clean(value) == value

    @pytest.mark.parametrize('value, is_required, valid', [
        ('http://', True, False),
        ('http://', False, True),

        ('ftp://', True, False),
        ('ftp://', False, True),

        ('invalid', True, False),
        ('invalid', False, False),
    ])
    def test_it_accepts_scheme_only_urls_if_not_required(self, value,
                                                         is_required, valid):
        field = RelaxedURL(default_scheme=value, required=is_required)
        if valid:
            assert field.clean(value) is None
        else:
            with pytest.raises(ValidationError) as e:
                field.clean(value)
            assert e.value.args[0] == 'Invalid URL.'

    @pytest.mark.parametrize('value', [23.0, True])
    def test_it_enforces_valid_data_type(self, value):
        with pytest.raises(ValidationError) as e:
            RelaxedURL().clean(value)
        assert e.value.args[0] in (
            'Value must be of basestring type.',
            'Value must be of str type.',
        )


class TestEmbeddedField:

    @pytest.fixture
    def schema_cls(self):
        class UserSchema(Schema):
            email = Email()
        return UserSchema

    def test_it_accepts_valid_input(self, schema_cls):
        value = {'email': 'valid@example.com'}
        assert Embedded(schema_cls).clean(value) == value

    def test_it_performs_validation_of_embedded_schema(self, schema_cls):
        value = {'email': 'invalid'}
        with pytest.raises(ValidationError) as e:
            Embedded(schema_cls).clean(value)
        assert e.value.args[0] == {
            'errors': [],
            'field-errors': {
                'email': 'Invalid email address.'
            }
        }

    @pytest.mark.parametrize('value', [{}, None])
    def test_it_enforces_required_flag(self, value, schema_cls):
        with pytest.raises(ValidationError) as e:
            Embedded(schema_cls).clean(value)
        assert e.value.args[0] == 'This field is required.'


class TestSchemaExternalClean:
    """
    Collection of tests making sure Schema#external_clean works as
    expected.
    """

    @pytest.fixture
    def message_schema_cls(self):

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

        return MessageSchema

    @pytest.fixture
    def email_schema_cls(self, message_schema_cls):

        # Specific email schema that also calls the generic message schema
        # via external_clean
        class EmailSchema(Schema):
            subject = String()

            def full_clean(self):
                super(EmailSchema, self).full_clean()
                self.external_clean(message_schema_cls)

        return EmailSchema

    def test_external_clean(self, email_schema_cls):
        schema = email_schema_cls({'subject': 'hi', 'status': 'sent'})
        schema.full_clean()
        assert schema.data == {
            'subject': 'hi',
            'status': 'sent',
            'message_cleaned': True,
        }

    def test_orig_data_in_external_clean(self, email_schema_cls):
        """
        Create a schema for an existing object, which originally had
        subject='hi' and status='sent' and we're trying to validate an
        update to subject='hi updated' and status='inbox' (which shouldn't
        be allowed).
        """
        orig_data = {'subject': 'hi', 'status': 'sent'}
        new_data = {'subject': 'hi updated', 'status': 'inbox'}
        schema = email_schema_cls(new_data, orig_data)

        pytest.raises(ValidationError, schema.full_clean)
        assert schema.field_errors == {
            'status': "Can't change from sent to inbox"
        }


class TestSchema:

    def test_empty_data_dict_with_required_fields(self):
        class RequiredSchema(Schema):
            text = String()

        schema = RequiredSchema({})
        pytest.raises(ValidationError, schema.full_clean)
        assert schema.field_errors['text'] == 'This field is required.'

    def test_blank_values_for_optional_fields(self):
        class OptionalSchema(Schema):
            text = String(required=False)
            boolean = Bool(required=False)
            number = Integer(required=False)

        data = OptionalSchema({}).full_clean()
        assert data == {
            'text': '',
            'boolean': False,
            'number': None,
        }

    def test_it_preserves_orig_data_if_no_new_data_given(self):
        class OptionalSchema(Schema):
            text = String(required=False)

        orig_data = {'text': 'old value'}
        data = OptionalSchema({}, orig_data).full_clean()
        assert data == orig_data

    @pytest.mark.parametrize('old_data, new_data, is_valid', [
        (None, {'text': 'hello'}, True),
        ({}, {'text': 'hello'}, True),
        ({'text': 'existing'}, {'text': 'existing'}, True),
        ({'text': 'existing'}, {}, True),
        ({'text': 'existing'}, {'text': 'new'}, False),
        ({'text': ''}, {'text': 'new'}, False),
        ({'text': None}, {'text': 'new'}, False),
    ])
    def test_it_enforces_mutability(self, old_data, new_data, is_valid):
        class UnmutableSchema(Schema):
            text = String(mutable=False)

        if old_data is None:
            schema = UnmutableSchema(new_data)
        else:
            schema = UnmutableSchema(new_data, old_data)

        if is_valid:
            assert schema.full_clean() == new_data or old_data
        else:
            with pytest.raises(ValidationError) as e:
                schema.full_clean()
            assert e.value.args[0] == {
                'errors': [],
                'field-errors': {
                    'text': 'Value cannot be changed.'
                }
            }

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

        schema = TestSchema({'value_id': 'val_xyz'})

        schema.full_clean()
        assert schema.data == {'value': 'val_xyz'}

        serialized = schema.serialize()
        assert serialized == {'value_id': 'val_xyz'}

    def test_raw_field_name_error(self):
        class TestSchema(Schema):
            value = Integer(raw_field_name='value_id')

        schema = TestSchema({'value_id': 'not-an-integer'})

        with pytest.raises(ValidationError):
            schema.full_clean()

        assert schema.field_errors == {
            'value_id': 'Value must be of int type.'
        }
