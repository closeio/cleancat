import unittest

from cleancat import ValidationError


def compare_dict_keys(data, keys, test_true=True):
    if isinstance(keys, list):
        keys = dict((key, None) for key in keys)
    for k, v in keys.items():
        assert k in data, 'Key %r not in %r' % (k, data)
        if test_true:
            assert data.get(k), 'Key %r is None in %r' % (k, data)
        if isinstance(v, dict) or isinstance(v, list):
            compare_dict_keys(data[k], v)
    for k, v in data.items():
        if test_true:
            assert not v or k in keys, 'Key %r is unexpectedly true in %r' % (k, data)
        else:
            assert k in keys, 'Key %r is unexpected in %r' % (k, data)


def compare_req_resp(req_obj, resp_obj):
    for k, v in req_obj.items():
        assert k in resp_obj.keys(), 'Key %r not in response (keys are %r)' % (k, resp_obj.keys())
        assert resp_obj[k] == v, 'Value for key %r should be %r but is %r' % (k, v, resp_obj[k])


class ValidationTestCase(unittest.TestCase):
    def assertValid(self, schema, data):
        compare_req_resp(data, schema.full_clean())

    def assertInvalid(self, schema, error_keys=None, error_obj=None):
        self.assertRaises(ValidationError, schema.full_clean)
        if error_keys:
            compare_dict_keys({'errors': schema.errors, 'field-errors': schema.field_errors}, error_keys)
        if error_obj:
            self.assertEqual(schema.field_errors, error_obj.get('field-errors', []))
            self.assertEqual(schema.errors, error_obj.get('errors', []))
