# -*- coding: utf-8 -*-
import datetime
import enum
import re
import unittest

import pytest

from cleancat import (
    Bool, Choices, DateTime, Dict, Email, Embedded, Enum, Field, Integer,
    List, Regex, RelaxedURL, Schema, SortedSet, StopValidation, String,
    TrimmedString, URL, ValidationError
)
from cleancat.utils import ValidationTestCase


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


class FieldTestCase(ValidationTestCase):
    def test_string(self):
        class TextSchema(Schema):
            text = String()  # required by default

        class OptionalTextSchema(Schema):
            text = String(required=False)

        self.assertInvalid(TextSchema({}), {'field-errors': ['text']})
        self.assertInvalid(TextSchema({'text': ''}), {'field-errors': ['text']})
        self.assertInvalid(TextSchema({'text': None}), {'field-errors': ['text']})
        self.assertValid(OptionalTextSchema({'text': ''}), {'text': ''})
        self.assertValid(OptionalTextSchema({'text': None}), {'text': ''})
        self.assertValid(OptionalTextSchema({}), {'text': ''})

    def test_trimmed_string(self):
        class TextSchema(Schema):
            text = TrimmedString()  # required by default

        class OptionalTextSchema(Schema):
            text = TrimmedString(required=False)

        class TextLengthSchema(Schema):
            text_min = TrimmedString(required=False, min_length=3)
            text_max = TrimmedString(required=False, max_length=8)
            text_min_max = TrimmedString(required=False, min_length=3, max_length=8)

        self.assertInvalid(TextSchema({}), {'field-errors': ['text']})
        self.assertValid(OptionalTextSchema({}), {'text': ''})

    def test_bool(self):
        class FlagSchema(Schema):
            flag = Bool()

        class OptionalFlagSchema(Schema):
            flag = Bool(required=False)

        self.assertValid(FlagSchema({'flag': True}), {'flag': True})
        self.assertValid(FlagSchema({'flag': False}), {'flag': False})
        self.assertInvalid(FlagSchema({'flag': None}), {'field-errors': ['flag']})
        self.assertInvalid(FlagSchema({}), {'field-errors': ['flag']})
        self.assertInvalid(FlagSchema({'flag': ''}), {'field-errors': ['flag']})

        self.assertValid(OptionalFlagSchema({'flag': True}), {'flag': True})
        self.assertValid(OptionalFlagSchema({'flag': False}), {'flag': False})
        self.assertValid(OptionalFlagSchema({'flag': None}), {'flag': False})
        self.assertValid(OptionalFlagSchema({}), {'flag': False})
        self.assertInvalid(OptionalFlagSchema({'flag': ''}), {'field-errors': ['flag']})

    def test_regex(self):
        class RegexSchema(Schema):
            letter = Regex('^[a-z]$')

        class RegexOptionsSchema(Schema):
            letter = Regex('^[a-z]$', re.IGNORECASE)

        class RegexMessageSchema(Schema):
            letter = Regex('^[a-z]$', regex_message='Not a lowercase letter.')

        class OptionalRegexMessageSchema(Schema):
            letter = Regex('^[a-z]$', regex_message='Not a lowercase letter.',
                           required=False)

        self.assertValid(RegexSchema({'letter': 'a'}), {'letter': 'a'})
        self.assertInvalid(RegexSchema({'letter': 'A'}), {'field-errors': ['letter']})
        self.assertInvalid(RegexSchema({'letter': ''}), {'field-errors': ['letter']})
        self.assertInvalid(RegexSchema({'letter': 'aa'}), {'field-errors': ['letter']})

        self.assertValid(RegexOptionsSchema({'letter': 'a'}), {'letter': 'a'})
        self.assertValid(RegexOptionsSchema({'letter': 'A'}), {'letter': 'A'})
        self.assertInvalid(RegexOptionsSchema({'letter': ''}), {'field-errors': ['letter']})
        self.assertInvalid(RegexOptionsSchema({'letter': 'aa'}), {'field-errors': ['letter']})

        self.assertValid(RegexMessageSchema({'letter': 'a'}), {'letter': 'a'})

        schema = RegexMessageSchema({'letter': ''})
        self.assertInvalid(schema, {'field-errors': ['letter']})
        assert schema.field_errors['letter'] == 'This field is required.'

        schema = RegexMessageSchema({'letter': 'aa'})
        self.assertInvalid(schema, {'field-errors': ['letter']})
        assert schema.field_errors['letter'] == 'Not a lowercase letter.'

        self.assertValid(OptionalRegexMessageSchema({'letter': 'a'}), {'letter': 'a'})
        self.assertValid(OptionalRegexMessageSchema({'letter': ''}), {'letter': ''})

        schema = OptionalRegexMessageSchema({'letter': 'aa'})
        self.assertInvalid(schema, {'field-errors': ['letter']})
        assert schema.field_errors['letter'] == 'Not a lowercase letter.'

    def test_datetime(self):
        class DateTimeSchema(Schema):
            dt = DateTime()

        from pytz import utc

        self.assertValid(
            DateTimeSchema({'dt': '2012-10-09'}),
            {'dt': datetime.date(2012, 10, 9)}
        )
        self.assertValid(
            DateTimeSchema({'dt': '2012-10-09 13:10:04'}),
            {'dt': datetime.datetime(2012, 10, 9, 13, 10, 4)}
        )
        self.assertValid(
            DateTimeSchema({'dt': '2013-03-27T01:24:50.137000+00:00'}),
            {'dt': datetime.datetime(2013, 3, 27, 1, 24, 50, 137000, tzinfo=utc)}
        )
        self.assertInvalid(
            DateTimeSchema({'dt': '0000-01-01T00:00:00-08:00'}),
            {'field-errors': ['dt']}
        )
        self.assertInvalid(
            DateTimeSchema({'dt': '2012a'}),
            {'field-errors': ['dt']}
        )
        self.assertInvalid(
            DateTimeSchema({'dt': ''}),
            {'field-errors': ['dt']}
        )
        self.assertInvalid(
            DateTimeSchema({'dt': None}),
            {'field-errors': ['dt']}
        )

        class OptionalDateTimeSchema(Schema):
            dt = DateTime(required=False)

        self.assertValid(OptionalDateTimeSchema({'dt': ''}), {'dt': None})

    def test_email(self):
        class EmailSchema(Schema):
            email = Email(required=True)

        class OptionalEmailSchema(Schema):
            email = Email(required=False)

        # Emails must not be longer than 254 characters.
        valid_email = '{u}@{d}.{d}.{d}.example'.format(u='u' * 54, d='d' * 63)
        invalid_email = '{u}@{d}.{d}.{d}.example'.format(u='u' * 55, d='d' * 63)

        self.assertValid(EmailSchema({'email': 'test@example.com'}), {'email': 'test@example.com'})
        self.assertValid(EmailSchema({'email': valid_email}), {'email': valid_email})
        schema = EmailSchema({'email': 'test@example'})
        self.assertInvalid(schema, {'field-errors': ['email']})
        assert schema.field_errors['email'] == 'Invalid email address.'
        self.assertInvalid(EmailSchema({'email': 'test.example.com'}), {'field-errors': ['email']})
        self.assertInvalid(EmailSchema({'email': invalid_email}), {'field-errors': ['email']})
        self.assertInvalid(EmailSchema({'email': None}), {'field-errors': ['email']})
        self.assertInvalid(EmailSchema({}), {'field-errors': ['email']})
        self.assertInvalid(EmailSchema({'email': ''}), {'field-errors': ['email']})

        self.assertValid(OptionalEmailSchema({'email': 'test@example.com'}), {'email': 'test@example.com'})
        self.assertValid(OptionalEmailSchema({'email': ''}), {'email': ''})
        self.assertValid(OptionalEmailSchema({'email': None}), {'email': ''})
        self.assertValid(OptionalEmailSchema({}), {'email': ''})
        self.assertInvalid(OptionalEmailSchema({'email': 'test@example'}), {'field-errors': ['email']})
        self.assertInvalid(OptionalEmailSchema({'email': 'test.example.com'}), {'field-errors': ['email']})

        # test auto-trimming
        self.assertValid(OptionalEmailSchema({'email': '   test@example.com   '}), {'email': 'test@example.com'})

    def test_integer(self):
        class AgeSchema(Schema):
            age = Integer()

        class OptionalAgeSchema(Schema):
            age = Integer(required=False)

        class AgeValueSchema(Schema):
            age_min_max = Integer(min_value=18, max_value=60, required=False)
            age_max = Integer(max_value=60, required=False)
            age_min = Integer(min_value=18, required=False)

        self.assertValid(AgeSchema({'age': 0}), {'age': 0})
        self.assertValid(AgeSchema({'age': 100}), {'age': 100})
        self.assertInvalid(AgeSchema({'age': None}), {'field-errors': ['age']})
        self.assertInvalid(AgeSchema({'age': 0.5}), {'field-errors': ['age']})

        self.assertValid(OptionalAgeSchema({'age': None}), {'age': None})
        self.assertValid(OptionalAgeSchema({'age': 0}), {'age': 0})
        self.assertInvalid(OptionalAgeSchema({'age': ''}), {'field-errors': ['age']})
        self.assertInvalid(OptionalAgeSchema({'age': 0.5}), {'field-errors': ['age']})

        self.assertInvalid(AgeValueSchema({'age_min_max': 17}, {'field-errors': ['age_min_max']}))
        self.assertValid(AgeValueSchema({'age_min_max': 18}), {'age_min_max': 18})
        self.assertValid(AgeValueSchema({'age_min_max': 40}), {'age_min_max': 40})
        self.assertValid(AgeValueSchema({'age_min_max': 60}), {'age_min_max': 60})
        self.assertInvalid(AgeValueSchema({'age_min_max': 61}, {'field-errors': ['age_min_max']}))

        self.assertValid(AgeValueSchema({'age_max': 60}), {'age_max': 60})
        self.assertInvalid(AgeValueSchema({'age_max': 61}, {'field-errors': ['age_max']}))

        self.assertInvalid(AgeValueSchema({'age_min': 17}, {'field-errors': ['age_min']}))
        self.assertValid(AgeValueSchema({'age_min': 18}), {'age_min': 18})

    def test_list(self):
        class TagsSchema(Schema):
            tags = List(String())

        class OptionalTagsSchema(Schema):
            tags = List(String(), required=False)

        class SmallTagsSchema(Schema):
            tags = List(String(), max_length=2)

        self.assertValid(TagsSchema({'tags': ['python', 'ruby']}), {'tags': ['python', 'ruby']})
        self.assertInvalid(TagsSchema({'tags': []}), {'field-errors': ['tags']})
        self.assertInvalid(TagsSchema({'tags': None}), {'field-errors': ['tags']})
        self.assertInvalid(TagsSchema({}), {'field-errors': ['tags']})

        self.assertValid(OptionalTagsSchema({'tags': ['python', 'ruby']}), {'tags': ['python', 'ruby']})
        self.assertValid(OptionalTagsSchema({'tags': []}), {'tags': []})
        self.assertValid(OptionalTagsSchema({'tags': None}), {'tags': []})
        self.assertValid(OptionalTagsSchema({}), {'tags': []})

        self.assertValid(SmallTagsSchema({'tags': ['python', 'ruby']}), {'tags': ['python', 'ruby']})
        self.assertInvalid(SmallTagsSchema({'tags': []}), {'field-errors': ['tags']})
        self.assertInvalid(SmallTagsSchema({'tags': ['python', 'ruby', 'go']}), {'field-errors': ['tags']})

    def test_sorted_set(self):
        class TagsSchema(Schema):
            tags = SortedSet(String())

        class OptionalTagsSchema(Schema):
            tags = SortedSet(String(), required=False)

        # Deduplicated
        self.assertValid(TagsSchema({'tags': ['python', 'ruby', 'python']}), {'tags': ['python', 'ruby']})

        # Sorted
        self.assertValid(TagsSchema({'tags': ['ruby', 'python']}), {'tags': ['python', 'ruby']})

        # Other cases just like in a List
        self.assertInvalid(TagsSchema({'tags': []}), {'field-errors': ['tags']})
        self.assertInvalid(TagsSchema({'tags': None}), {'field-errors': ['tags']})
        self.assertInvalid(TagsSchema({}), {'field-errors': ['tags']})

        self.assertValid(OptionalTagsSchema({'tags': ['ruby']}), {'tags': ['ruby']})
        self.assertValid(OptionalTagsSchema({'tags': []}), {'tags': []})
        self.assertValid(OptionalTagsSchema({'tags': None}), {'tags': []})
        self.assertValid(OptionalTagsSchema({}), {'tags': []})

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

    def test_required_1(self):
        class RequiredSchema(Schema):
            text = String()

        self.assertValid(RequiredSchema({'text': 'hello'}), {'text': 'hello'})
        self.assertInvalid(RequiredSchema({'text': ''}), {'field-errors': ['text']})

        self.assertInvalid(RequiredSchema({'text': ''}, {}), {'field-errors': ['text']})
        self.assertInvalid(RequiredSchema({'text': ''}, {'text': ''}), {'field-errors': ['text']})
        self.assertInvalid(RequiredSchema({'text': ''}, {'text': 'existing'}), {'field-errors': ['text']})

        self.assertInvalid(RequiredSchema({}, {}), {'field-errors': ['text']})
        self.assertInvalid(RequiredSchema({}, {'text': ''}), {'field-errors': ['text']})
        self.assertValid(RequiredSchema({}, {'text': 'existing'}), {'text': 'existing'})

    def test_required_2(self):
        class RequiredSchema(Schema):
            flag = Bool()

        self.assertValid(RequiredSchema({'flag': True}), {'flag': True})
        self.assertValid(RequiredSchema({'flag': False}), {'flag': False})
        self.assertInvalid(RequiredSchema({'flag': None}), {'field-errors': ['flag']})
        self.assertInvalid(RequiredSchema({}), {'field-errors': ['flag']})

        self.assertValid(RequiredSchema({'flag': True}, {}), {'flag': True})
        self.assertValid(RequiredSchema({'flag': False}, {}), {'flag': False})
        self.assertInvalid(RequiredSchema({'flag': None}, {}), {'field-errors': ['flag']})
        self.assertInvalid(RequiredSchema({}, {}), {'field-errors': ['flag']})

        self.assertValid(RequiredSchema({'flag': True}, {'flag': True}), {'flag': True})
        self.assertValid(RequiredSchema({'flag': False}, {'flag': True}), {'flag': False})
        self.assertInvalid(RequiredSchema({'flag': None}, {'flag': True}), {'field-errors': ['flag']})
        self.assertValid(RequiredSchema({}, {'flag': True}), {'flag': True})

        self.assertValid(RequiredSchema({'flag': True}, {'flag': False}), {'flag': True})
        self.assertValid(RequiredSchema({'flag': False}, {'flag': False}), {'flag': False})
        self.assertInvalid(RequiredSchema({'flag': None}, {'flag': False}), {'field-errors': ['flag']})
        self.assertValid(RequiredSchema({}, {'flag': False}), {'flag': False})

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

    def test_multiple_base_types(self):
        class IntOrStrField(Field):
            base_type = (int, str)

        class TestSchema(Schema):
            id = IntOrStrField()

        self.assertValid(TestSchema({'id': 5}), {'id': 5})
        self.assertValid(TestSchema({'id': 'five'}), {'id': 'five'})

        schema = TestSchema({'id': 4.5})
        self.assertInvalid(schema, {'field-errors': ['id']})
        assert schema.field_errors['id'] == 'Value must be of int or str type.'


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


class SerializationTestCase(unittest.TestCase):
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


def test_raw_field_name_serialization():
    class TestSchema(Schema):
        value = String(raw_field_name='value_id')

    schema = TestSchema(raw_data={'value_id': 'val_xyz'})

    schema.full_clean()
    assert schema.data == {'value': 'val_xyz'}

    serialized = schema.serialize()
    assert serialized == {'value_id': 'val_xyz'}


def test_raw_field_name_error():
    class TestSchema(Schema):
        value = Integer(raw_field_name='value_id')

    schema = TestSchema(raw_data={'value_id': 'not-an-integer'})

    with pytest.raises(ValidationError):
        schema.full_clean()

    assert schema.field_errors == {
        'value_id': 'Value must be of int type.'
    }


if __name__ == '__main__':
    unittest.main()
