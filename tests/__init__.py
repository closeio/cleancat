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
        self.assertInvalid(TextSchema({'text': ''}), {'errors': ['text']})
        self.assertInvalid(TextSchema({'text': None}), {'errors': ['text']})
        self.assertInvalid(TextSchema({}), {'errors': ['text']})
        self.assertInvalid(TextSchema({'text': True}), {'errors': ['text']})

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
        self.assertInvalid(FlagSchema({'flag': None}), {'errors': ['flag']})
        self.assertInvalid(FlagSchema({}), {'errors': ['flag']})
        self.assertInvalid(FlagSchema({'flag': ''}), {'errors': ['flag']})

        self.assertValid(OptionalFlagSchema({'flag': True}), {'flag': True})
        self.assertValid(OptionalFlagSchema({'flag': False}), {'flag': False})
        self.assertValid(OptionalFlagSchema({'flag': None}), {'flag': False})
        self.assertValid(OptionalFlagSchema({}), {'flag': False})
        self.assertInvalid(OptionalFlagSchema({'flag': ''}), {'errors': ['flag']})

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
        self.assertInvalid(RegexSchema({'letter': 'A'}), {'errors': ['letter']})
        self.assertInvalid(RegexSchema({'letter': ''}), {'errors': ['letter']})
        self.assertInvalid(RegexSchema({'letter': 'aa'}), {'errors': ['letter']})

        self.assertValid(RegexOptionsSchema({'letter': 'a'}), {'letter': 'a'})
        self.assertValid(RegexOptionsSchema({'letter': 'A'}), {'letter': 'A'})
        self.assertInvalid(RegexOptionsSchema({'letter': ''}), {'errors': ['letter']})
        self.assertInvalid(RegexOptionsSchema({'letter': 'aa'}), {'errors': ['letter']})

        self.assertValid(RegexMessageSchema({'letter': 'a'}), {'letter': 'a'})

        schema = RegexMessageSchema({'letter': ''})
        self.assertInvalid(schema, {'errors': ['letter']})
        self.assertEqual(schema.errors['letter'], u'This field is required.')

        schema = RegexMessageSchema({'letter': 'aa'})
        self.assertInvalid(schema, {'errors': ['letter']})
        self.assertEqual(schema.errors['letter'], u'Not a lowercase letter.')

        self.assertValid(OptionalRegexMessageSchema({'letter': 'a'}), {'letter': 'a'})
        self.assertValid(OptionalRegexMessageSchema({'letter': ''}), {'letter': ''})

        schema = OptionalRegexMessageSchema({'letter': 'aa'})
        self.assertInvalid(schema, {'errors': ['letter']})
        self.assertEqual(schema.errors['letter'], u'Not a lowercase letter.')

    def test_datetime(self):
        class DateTimeSchema(Schema):
            dt = DateTime()

        self.assertValid(DateTimeSchema({'dt': '2012-10-09'}), {'dt': datetime.date(2012,10,9)})
        self.assertValid(DateTimeSchema({'dt': '2012-10-09 13:10:04'}), {'dt': datetime.datetime(2012,10,9, 13,10,04)})
        self.assertInvalid(DateTimeSchema({'dt': '2012a'}), {'errors': ['dt']})
        self.assertInvalid(DateTimeSchema({'dt': ''}), {'errors': ['dt']})
        self.assertInvalid(DateTimeSchema({'dt': None}), {'errors': ['dt']})

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
        self.assertInvalid(schema, {'errors': ['email']})
        self.assertEqual(schema.errors['email'], u'Invalid email address.')
        self.assertInvalid(EmailSchema({'email': 'test.example.com'}), {'errors': ['email']})
        self.assertInvalid(EmailSchema({'email': None}), {'errors': ['email']})
        self.assertInvalid(EmailSchema({}), {'errors': ['email']})
        self.assertInvalid(EmailSchema({'email': ''}), {'errors': ['email']})

        self.assertValid(OptionalEmailSchema({'email': 'test@example.com'}), {'email': 'test@example.com'})
        self.assertValid(OptionalEmailSchema({'email': ''}), {'email': ''})
        self.assertValid(OptionalEmailSchema({'email': None}), {'email': ''})
        self.assertValid(OptionalEmailSchema({}), {'email': ''})
        self.assertInvalid(OptionalEmailSchema({'email': 'test@example'}), {'errors': ['email']})
        self.assertInvalid(OptionalEmailSchema({'email': 'test.example.com'}), {'errors': ['email']})

    def test_integer(self):
        class AgeSchema(Schema):
            age = Integer()

        class OptionalAgeSchema(Schema):
            age = Integer(required=False)

        self.assertValid(AgeSchema({'age': 0}), {'age': 0})
        self.assertValid(AgeSchema({'age': 100}), {'age': 100})
        self.assertInvalid(AgeSchema({'age': None}), {'errors': ['age']})
        self.assertInvalid(AgeSchema({'age': 0.5}), {'errors': ['age']})

        self.assertValid(OptionalAgeSchema({'age': None}), {'age': None})
        self.assertValid(OptionalAgeSchema({'age': 0}), {'age': 0})
        self.assertInvalid(OptionalAgeSchema({'age': ''}), {'errors': ['age']})
        self.assertInvalid(OptionalAgeSchema({'age': 0.5}), {'errors': ['age']})

    def test_list(self):
        class TagsSchema(Schema):
            tags = List(String())

        class OptionalTagsSchema(Schema):
            tags = List(String(), required=False)

        self.assertValid(TagsSchema({'tags': ['python', 'ruby']}), {'tags': ['python', 'ruby']})
        self.assertInvalid(TagsSchema({'tags': []}), {'errors': ['tags']})
        self.assertInvalid(TagsSchema({'tags': None}), {'errors': ['tags']})
        self.assertInvalid(TagsSchema({}), {'errors': ['tags']})

        self.assertValid(OptionalTagsSchema({'tags': ['python', 'ruby']}), {'tags': ['python', 'ruby']})
        self.assertValid(OptionalTagsSchema({'tags': []}), {'tags': []})
        self.assertValid(OptionalTagsSchema({'tags': None}), {'tags': []})
        self.assertValid(OptionalTagsSchema({}), {'tags': []})


    # TODO: Test Embedded, Choices, MongoReference, more Schema tests.

if __name__ == '__main__':
    unittest.main()
