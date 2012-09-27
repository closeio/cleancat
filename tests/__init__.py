import unittest
from cleancat import *


def compare_dict_keys(data, keys, test_true=True):
    if isinstance(keys, list):
        keys = dict((key, None) for key in keys)
    for k, v in keys.iteritems():
        assert k in data, 'Key %r not in %r' % (k, data)
        if test_true:
            assert data.get(k), 'Key %r is None in %r' % (k, data)
        if isinstance(v, dict) or isinstance(v, list):
            compare_dict_keys(data[k], v)
    for k, v in data.iteritems():
        if test_true:
            assert not v or k in keys, 'Key %r is unexpectedly true in %r' % (k, data)
        else:
            assert k in keys, 'Key %r is unexpected in %r' % (k, data)

class ValidationTestCase(unittest.TestCase):
    def assertValid(self, schema, data):
        self.assertEqual(schema.full_clean(), data)

    def assertInvalid(self, schema, error_keys=None):
        self.assertRaises(ValidationError, schema.full_clean)
        if error_keys:
            compare_dict_keys({'errors': schema.errors, 'non-field-errors': schema.non_field_errors}, error_keys)

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


    # TODO: Test Email, Embedded, Choices, MongoReference, more Schema tests.

if __name__ == '__main__':
    unittest.main()
