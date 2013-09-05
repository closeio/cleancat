import unittest
import datetime
from cleancat import *
from cleancat.utils import ValidationTestCase

class FieldTestCase(ValidationTestCase):
    def test_string(self):
        class TextSchema(Schema):
            text = String() # required by default

        class OptionalTextSchema(Schema):
            text = String(required=False)


        self.assertValid(TextSchema({'text': 'hello world'}), {'text': 'hello world'})
        self.assertInvalid(TextSchema({'text': ''}), {'field-errors': ['text']})
        self.assertInvalid(TextSchema({'text': None}), {'field-errors': ['text']})
        self.assertInvalid(TextSchema({}), {'field-errors': ['text']})
        self.assertInvalid(TextSchema({'text': True}), {'field-errors': ['text']})

        self.assertValid(OptionalTextSchema({'text': 'hello world'}), {'text': 'hello world'})
        self.assertValid(OptionalTextSchema({'text': ''}), {'text': ''})
        self.assertValid(OptionalTextSchema({'text': None}), {'text': ''})
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
            letter = Regex('^[a-z]$', regex_message=u'Not a lowercase letter.')
        class OptionalRegexMessageSchema(Schema):
            letter = Regex('^[a-z]$', regex_message=u'Not a lowercase letter.', required=False)

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
        self.assertEqual(schema.field_errors['letter'], u'This field is required.')

        schema = RegexMessageSchema({'letter': 'aa'})
        self.assertInvalid(schema, {'field-errors': ['letter']})
        self.assertEqual(schema.field_errors['letter'], u'Not a lowercase letter.')

        self.assertValid(OptionalRegexMessageSchema({'letter': 'a'}), {'letter': 'a'})
        self.assertValid(OptionalRegexMessageSchema({'letter': ''}), {'letter': ''})

        schema = OptionalRegexMessageSchema({'letter': 'aa'})
        self.assertInvalid(schema, {'field-errors': ['letter']})
        self.assertEqual(schema.field_errors['letter'], u'Not a lowercase letter.')

    def test_datetime(self):
        class DateTimeSchema(Schema):
            dt = DateTime()

        from pytz import utc

        self.assertValid(DateTimeSchema({'dt': '2012-10-09'}), {'dt': datetime.date(2012,10,9)})
        self.assertValid(DateTimeSchema({'dt': '2012-10-09 13:10:04'}), {'dt': datetime.datetime(2012,10,9, 13,10,04)})
        self.assertValid(DateTimeSchema({'dt': '2013-03-27T01:24:50.137000+00:00'}), {'dt': datetime.datetime(2013,3,27, 1,24,50, 137000, tzinfo=utc)})
        self.assertInvalid(DateTimeSchema({'dt': '0000-01-01T00:00:00-08:00'}), {'field-errors': ['dt']})
        self.assertInvalid(DateTimeSchema({'dt': '2012a'}), {'field-errors': ['dt']})
        self.assertInvalid(DateTimeSchema({'dt': ''}), {'field-errors': ['dt']})
        self.assertInvalid(DateTimeSchema({'dt': None}), {'field-errors': ['dt']})

        class OptionalDateTimeSchema(Schema):
            dt = DateTime(required=False)

        self.assertValid(OptionalDateTimeSchema({'dt': ''}), {'dt': None})

    def test_email(self):
        class EmailSchema(Schema):
            email = Email(required=True)

        class OptionalEmailSchema(Schema):
            email = Email(required=False)

        self.assertValid(EmailSchema({'email': 'test@example.com'}), {'email': 'test@example.com'})
        schema = EmailSchema({'email': 'test@example'})
        self.assertInvalid(schema, {'field-errors': ['email']})
        self.assertEqual(schema.field_errors['email'], u'Invalid email address.')
        self.assertInvalid(EmailSchema({'email': 'test.example.com'}), {'field-errors': ['email']})
        self.assertInvalid(EmailSchema({'email': None}), {'field-errors': ['email']})
        self.assertInvalid(EmailSchema({}), {'field-errors': ['email']})
        self.assertInvalid(EmailSchema({'email': ''}), {'field-errors': ['email']})

        self.assertValid(OptionalEmailSchema({'email': 'test@example.com'}), {'email': 'test@example.com'})
        self.assertValid(OptionalEmailSchema({'email': ''}), {'email': ''})
        self.assertValid(OptionalEmailSchema({'email': None}), {'email': ''})
        self.assertValid(OptionalEmailSchema({}), {'email': ''})
        self.assertInvalid(OptionalEmailSchema({'email': 'test@example'}), {'field-errors': ['email']})
        self.assertInvalid(OptionalEmailSchema({'email': 'test.example.com'}), {'field-errors': ['email']})

    def test_integer(self):
        class AgeSchema(Schema):
            age = Integer()

        class OptionalAgeSchema(Schema):
            age = Integer(required=False)

        self.assertValid(AgeSchema({'age': 0}), {'age': 0})
        self.assertValid(AgeSchema({'age': 100}), {'age': 100})
        self.assertInvalid(AgeSchema({'age': None}), {'field-errors': ['age']})
        self.assertInvalid(AgeSchema({'age': 0.5}), {'field-errors': ['age']})

        self.assertValid(OptionalAgeSchema({'age': None}), {'age': None})
        self.assertValid(OptionalAgeSchema({'age': 0}), {'age': 0})
        self.assertInvalid(OptionalAgeSchema({'age': ''}), {'field-errors': ['age']})
        self.assertInvalid(OptionalAgeSchema({'age': 0.5}), {'field-errors': ['age']})

    def test_list(self):
        class TagsSchema(Schema):
            tags = List(String())

        class OptionalTagsSchema(Schema):
            tags = List(String(), required=False)

        self.assertValid(TagsSchema({'tags': ['python', 'ruby']}), {'tags': ['python', 'ruby']})
        self.assertInvalid(TagsSchema({'tags': []}), {'field-errors': ['tags']})
        self.assertInvalid(TagsSchema({'tags': None}), {'field-errors': ['tags']})
        self.assertInvalid(TagsSchema({}), {'field-errors': ['tags']})

        self.assertValid(OptionalTagsSchema({'tags': ['python', 'ruby']}), {'tags': ['python', 'ruby']})
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

    def test_url(self):
        class URLSchema(Schema):
            url = URL()

        self.assertValid(URLSchema({'url': 'http://example.com/a?b=c'}), {'url': 'http://example.com/a?b=c'})
        self.assertValid(URLSchema({'url': 'ftp://ftp.example.com'}), {'url': 'ftp://ftp.example.com'})
        self.assertInvalid(URLSchema({'url': 'www.example.com'}), {'field-errors': ['url']})
        self.assertInvalid(URLSchema({'url': 'invalid'}), {'field-errors': ['url']})

        class DefaultURLSchema(Schema):
            url = URL(default_scheme='http://')

        self.assertValid(DefaultURLSchema({'url': 'http://example.com/a?b=c'}), {'url': 'http://example.com/a?b=c'})
        self.assertValid(DefaultURLSchema({'url': 'ftp://ftp.example.com'}), {'url': 'ftp://ftp.example.com'})
        self.assertValid(DefaultURLSchema({'url': 'www.example.com'}), {'url': 'http://www.example.com'})
        self.assertInvalid(DefaultURLSchema({'url': 'invalid'}), {'field-errors': ['url']})
        self.assertInvalid(DefaultURLSchema({'url': True}), {'field-errors': ['url']})

        class RelaxedURLSchema(Schema):
            url = RelaxedURL(default_scheme='http://')

        self.assertValid(RelaxedURLSchema({'url': 'http://example.com/a?b=c'}), {'url': 'http://example.com/a?b=c'})
        self.assertValid(RelaxedURLSchema({'url': 'ftp://ftp.example.com'}), {'url': 'ftp://ftp.example.com'})
        self.assertValid(RelaxedURLSchema({'url': 'www.example.com'}), {'url': 'http://www.example.com'})
        self.assertInvalid(RelaxedURLSchema({'url': 'http://'}), {'field-errors': ['url']})
        self.assertInvalid(RelaxedURLSchema({'url': 'invalid'}), {'field-errors': ['url']})
        self.assertInvalid(RelaxedURLSchema({'url': True}), {'field-errors': ['url']})

        class OptionalRelaxedURLSchema(Schema):
            url = RelaxedURL(required=False, default_scheme='http://')

        self.assertValid(OptionalRelaxedURLSchema({'url': 'http://example.com/a?b=c'}), {'url': 'http://example.com/a?b=c'})
        self.assertValid(OptionalRelaxedURLSchema({'url': 'ftp://ftp.example.com'}), {'url': 'ftp://ftp.example.com'})
        self.assertValid(OptionalRelaxedURLSchema({'url': 'www.example.com'}), {'url': 'http://www.example.com'})
        self.assertValid(OptionalRelaxedURLSchema({'url': 'http://'}), {'url': None})
        self.assertInvalid(OptionalRelaxedURLSchema({'url': 'invalid'}), {'field-errors': ['url']})
        self.assertInvalid(OptionalRelaxedURLSchema({'url': True}), {'field-errors': ['url']})



    def test_embedded(self):
        class UserSchema(Schema):
            email = Email()

        class MemberSchema(Schema):
            user = Embedded(UserSchema)

        self.assertValid(MemberSchema({
            'user': { 'email': 'a@example.com' }
        }), {
            'user': { 'email': 'a@example.com' }
        })

        self.assertInvalid(MemberSchema({
            'user': { 'email': 'invalid' }
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
            'user': { }
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

    # TODO: Test MongoEmbedded, MongoReference, more Schema tests.

if __name__ == '__main__':
    unittest.main()
