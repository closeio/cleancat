import datetime
import re
import sys

import pytz
from dateutil import parser


if sys.version_info[0] == 3:
    basestring = str


class ValidationError(Exception):
    pass


class StopValidation(Exception):
    pass


class Field(object):
    base_type = None
    blank_value = None

    def __init__(self, required=True, default=None, field_name=None,
                 raw_field_name=None, mutable=True, read_only=False):
        """
        By default, the field name is derived from the schema model, but in
        certain cases it can be overridden. Specifying field_name overrides
        both the name of the field in the raw (unclean) data, as well as in the
        clean data model. If the raw data has a different field name than the
        clean data, raw_field_name can be overridden.
        """
        self.required = required
        self.default = default
        self.mutable = mutable
        self.field_name = field_name
        self.raw_field_name = raw_field_name or field_name
        self.read_only = read_only

    def has_value(self, value):
        return value is not None

    def clean(self, value):
        """
        Takes a dirty value and cleans it.
        """
        if self.base_type is not None and value is not None and not isinstance(value, self.base_type):
            raise ValidationError('Value must be of %s type.' % self.base_type.__name__)

        if not self.has_value(value):
            if self.default is not None:
                raise StopValidation(self.default)

            if self.required:
                raise ValidationError('This field is required.')
            else:
                raise StopValidation(self.blank_value)

        return value

    def serialize(self, value):
        """
        Takes a cleaned value and serializes it.
        """
        return value


class String(Field):
    base_type = basestring
    blank_value = ''
    min_length = None
    max_length = None

    def __init__(self, min_length=None, max_length=None, **kwargs):
        if min_length is not None:
            self.min_length = min_length
        if max_length is not None:
            self.max_length = max_length
        super(String, self).__init__(**kwargs)

    def _check_length(self, value):
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError('The value must be no longer than %s characters.' % self.max_length)

        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError('The value must be at least %s characters long.' % self.min_length)

    def clean(self, value):
        value = super(String, self).clean(value)
        self._check_length(value)
        return value

    def has_value(self, value):
        return bool(value)


class TrimmedString(String):
    base_type = basestring
    blank_value = ''

    def clean(self, value):
        value = super(String, self).clean(value)
        if value:
            value = value.strip()
        self._check_length(value)
        return value

    def has_value(self, value):
        return bool(value and value.strip())


class Bool(Field):
    base_type = bool
    blank_value = False


class Regex(String):
    regex = None
    regex_flags = 0
    regex_message = 'Invalid input.'

    def __init__(self, regex=None, regex_flags=None, regex_message=None, **kwargs):
        super(Regex, self).__init__(**kwargs)
        if regex is not None:
            self.regex = regex
        if regex_flags is not None:
            self.regex_flags = regex_flags
        if regex_message is not None:
            self.regex_message = regex_message

    def get_regex(self):
        return re.compile(self.regex, self.regex_flags)

    def clean(self, value):
        value = super(Regex, self).clean(value)

        if not self.get_regex().match(value):
            raise ValidationError(self.regex_message)

        return value


class DateTime(Regex):
    """ ISO 8601 from http://www.pelagodesign.com/blog/2009/05/20/iso-8601-date-validation-that-doesnt-suck/ """
    regex = "^([\\+-]?\\d{4}(?!\\d{2}\\b))((-?)((0[1-9]|1[0-2])(\\3([12]\\d|0[1-9]|3[01]))?|W([0-4]\\d|5[0-2])(-?[1-7])?|(00[1-9]|0[1-9]\\d|[12]\\d{2}|3([0-5]\\d|6[1-6])))([T\\s]((([01]\\d|2[0-3])((:?)[0-5]\\d)?|24\\:?00)([\\.,]\\d+(?!:))?)?(\\17[0-5]\\d([\\.,]\\d+)?)?([zZ]|([\\+-])([01]\\d|2[0-3]):?([0-5]\\d)?)?)?)?$"
    regex_message = 'Invalid ISO 8601 datetime.'
    blank_value = None

    def __init__(self, *args, **kwargs):
        self.min_date = kwargs.pop('min_date', None)
        super(DateTime, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(Regex, self).clean(value)
        match = self.get_regex().match(value)
        if not match:
            raise ValidationError(self.regex_message)
        try:
            dt = parser.parse(value)
        except Exception as e:
            raise ValidationError('Could not parse date: %s' % str(e))
        if self.min_date:
            if dt.tzinfo is not None and self.min_date.tzinfo is None:
                min_date = self.min_date.replace(tzinfo=pytz.utc)
            else:
                min_date = self.min_date
            if dt < min_date:
                raise ValidationError('Date cannot be earlier than %s.' % self.min_date.strftime('%Y-%m-%d'))
        time_group = match.groups()[11]
        if time_group and len(time_group) > 1:
            return dt
        return dt.date()

    def serialize(self, value):
        return value.isoformat()


class Email(Regex):
    regex = r'^.+@[^.].*\.[a-z]{2,63}$'
    regex_flags = re.IGNORECASE
    regex_message = 'Invalid email address.'
    max_length = 254

    def clean(self, value):
        # trim any leading/trailing whitespace before validating the email
        if isinstance(value, basestring):
            value = value.strip()
        return super(Email, self).clean(value)


class URL(Regex):
    blank_value = None

    def __init__(self, require_tld=True, default_scheme=None, allowed_schemes=None, **kwargs):
        # FQDN validation similar to https://github.com/chriso/validator.js/blob/master/src/lib/isFQDN.js

        # ff01-ff5f -> full-width chars, not allowed
        alpha_numeric_and_symbols_ranges = u'0-9a-z\u00a1-\uff00\uff5f-\uffff'

        tld_part = (require_tld and r'\.[%s-]{2,63}' % alpha_numeric_and_symbols_ranges or '')
        scheme_part = '[a-z]+://'
        self.default_scheme = default_scheme
        if self.default_scheme and not self.default_scheme.endswith('://'):
            self.default_scheme += '://'
        self.scheme_regex = re.compile('^' + scheme_part, re.IGNORECASE)
        if default_scheme:
            scheme_part = '(%s)?' % scheme_part
        regex = r'^%s([-%s@:%%_+.~#?&/\\=]{1,256}%s|([0-9]{1,3}\.){3}[0-9]{1,3})(:[0-9]+)?([/?].*)?$' % (scheme_part, alpha_numeric_and_symbols_ranges, tld_part)
        super(URL, self).__init__(regex=regex, regex_flags=re.IGNORECASE | re.UNICODE, regex_message='Invalid URL.', **kwargs)

        self.allowed_schemes = allowed_schemes or []
        self.allowed_schemes_regexes = []
        for sch in self.allowed_schemes:
            if not sch.endswith('://'):
                sch += '://'
            self.allowed_schemes_regexes.append(
                re.compile('^' + sch + '.*', re.IGNORECASE)
            )

    def clean(self, value):
        if value == self.blank_value:
            return value
        value = super(URL, self).clean(value)
        if not self.scheme_regex.match(value):
            value = self.default_scheme + value

        if self.allowed_schemes:
            allowed = False

            for allowed_regex in self.allowed_schemes_regexes:
                if allowed_regex.match(value):
                    allowed = True
                    break

            if not allowed:
                raise ValidationError("This URL uses a scheme that's not allowed. You can only use %s." % ' or '.join(self.allowed_schemes))

        return value


class RelaxedURL(URL):
    """Like URL but will just ignore values like "http://" and treat them as blank"""
    def clean(self, value):
        if not self.required and value == self.default_scheme:
            return None
        value = super(RelaxedURL, self).clean(value)
        return value


class Integer(Field):
    base_type = int

    def __init__(self, min_value=None, max_value=None, **kwargs):
        self.max_value = max_value
        self.min_value = min_value
        super(Integer, self).__init__(**kwargs)

    def _check_value(self, value):
        if self.max_value is not None and value > self.max_value:
            raise ValidationError('The value must not be larger than %d.' % self.max_value)

        if self.min_value is not None and value < self.min_value:
            raise ValidationError('The value must be at least %d.' % self.min_value)

    def clean(self, value):
        value = super(Integer, self).clean(value)
        self._check_value(value)
        return value


class List(Field):
    base_type = list
    blank_value = []

    def __init__(self, field_instance, max_length=None, **kwargs):
        self.max_length = max_length
        super(List, self).__init__(**kwargs)
        self.field_instance = field_instance

    def has_value(self, value):
        return bool(value)

    def clean(self, value):
        value = super(List, self).clean(value)

        item_cnt = len(value)
        if self.required and not item_cnt:
            raise ValidationError('List must not be empty.')

        if self.max_length and item_cnt > self.max_length:
            raise ValidationError('List is too long.')

        errors = {}
        data = []
        for n, item in enumerate(value):
            try:
                cleaned_data = self.field_instance.clean(item)
            except ValidationError as e:
                errors[n] = e.args and e.args[0]
            else:
                data.append(cleaned_data)

        if errors:
            raise ValidationError({
                'errors': errors
            })

        return data

    def serialize(self, value):
        return [self.field_instance.serialize(item) for item in value]


class Dict(Field):
    base_type = dict

    def has_value(self, value):
        return bool(value)


class Embedded(Dict):
    def __init__(self, schema_class, **kwargs):
        super(Embedded, self).__init__(**kwargs)
        self.schema_class = schema_class

    def clean(self, value):
        value = super(Embedded, self).clean(value)
        try:
            cleaned_value = self.schema_class(value).full_clean()
        except ValidationError as e:
            raise e
        else:
            return cleaned_value

    def is_valid(self):
        try:
            self.clean()
        except ValidationError:
            return False
        else:
            return True

    def serialize(self, value):
        return self.schema_class(data=value).serialize()


class Choices(Field):
    """
    A field that accepts the given choices.
    """
    def __init__(self, choices, case_insensitive=False, error_invalid_choice=None, **kwargs):
        super(Choices, self).__init__(**kwargs)
        self.choices = choices
        self.case_insensitive = case_insensitive
        self.error_invalid_choice = error_invalid_choice or 'Not a valid choice.'

    def get_choices(self):
        return self.choices

    def clean(self, value):
        value = super(Choices, self).clean(value)

        choices = self.get_choices()

        if self.case_insensitive:
            choices = {choice.lower(): choice for choice in choices}

            if not isinstance(value, basestring):
                raise ValidationError(u'Value needs to be a string.')

            if value.lower() not in choices:
                raise ValidationError(self.error_invalid_choice.format(value=value))

            return choices[value.lower()]

        if value not in choices:
            raise ValidationError(self.error_invalid_choice.format(value=value))

        return value


class Enum(Choices):
    """
    Like Choices, but expects a Python 3 Enum.
    """
    def get_choices(self):
        return [choice.value for choice in self.choices]

    def clean(self, value):
        value = super(Enum, self).clean(value)
        return self.choices(value)

    def serialize(self, choice):
        return choice.value


class SortedSet(List):
    """Sorted, unique set of values represented as a list."""
    def clean(self, value):
        return list(sorted(set(super(SortedSet, self).clean(value))))


class Schema(object):
    """
    Base Schema class. Provides core behavior like fields declaration
    and construction, validation, and data and error proxying.

    There are 3 steps to using a Schema:

    1. Define the Schema, e.g.

        class UserSchema(Schema):
            first_name = String()
            last_name = String()
            email = Email()

    2. Create a Schema instance, passing data into it.

        # Scenario 1: Creation of a new object.
        schema = UserSchema({
            'first_name': 'Donald',
            'last_name': 'Glover',
            'email': 'gambino@example.com'
        })

        # Scenario 2: Update of an existing object.
        schema = UserSchema(
            raw_data={
                'first_name': 'Childish',
                'last_name': 'Gambino'
            },
            data={
                'first_name': 'Donald',
                'last_name': 'Glover',
                'email': 'gambino@example.com'
            }
        )

    3. Clean the Schema (validating the data you passed into it).

        data = schema.full_clean()

    This operation will raise a ValidationError if the data you passed
    into the Schema is invalid.

    To introduce custom validation to the Schema (beyond the basics
    covered by various Field types), override the "clean" method and
    raise a ValidationError with a descriptive message if you encounter
    any invalid data.

    Parameters:
    - raw_data - a dict with the data you want to validate.
    - data - dict with existing data, e.g. based on some object you're
             trying to update.
    """

    @classmethod
    def get_fields(cls):
        """
        Returns a dictionary of fields and field instances for this schema.
        """
        fields = {}
        for field_name in dir(cls):
            if isinstance(getattr(cls, field_name), Field):
                field = getattr(cls, field_name)
                field_name = field.field_name or field_name
                fields[field_name] = field
        return fields

    @classmethod
    def obj_to_dict(cls, obj):
        """
        Takes a model object and converts it into a dictionary suitable for
        passing to the constructor's data attribute.
        """
        data = {}
        for field_name in cls.get_fields():
            if hasattr(obj, field_name):
                value = getattr(obj, field_name)
                if callable(value):
                    value = value()
                data[field_name] = value
        return data

    def __init__(self, raw_data=None, data=None):
        conflicting_fields = set([
            'raw_data', 'orig_data', 'data', 'errors', 'field_errors', 'fields'
        ]).intersection(dir(self))
        if conflicting_fields:
            raise Exception(
                'The following field names are reserved and need to be renamed: %s. '
                'Please use the field_name keyword to use them.' % list(conflicting_fields)
            )

        self.raw_data = raw_data or {}
        self.orig_data = data or None
        self.data = data and dict(data) or {}
        self.field_errors = {}
        self.errors = []
        self.fields = self.get_fields()

    def clean(self):
        pass

    def full_clean(self):
        if not isinstance(self.raw_data, dict):
            raise ValidationError({
                'errors': ['Invalid request: JSON dictionary expected.']
            })

        for field_name, field in self.fields.items():
            if field.read_only:
                continue
            raw_field_name = field.raw_field_name or field_name
            try:
                # Validate a field if it's posted in raw_data, or if we don't
                # have a value for it in case it's required.
                if raw_field_name in self.raw_data or not field.has_value(self.data.get(field_name, None)):
                    value = field.clean(self.raw_data.get(raw_field_name))
                    if not field.mutable and self.orig_data and field_name in self.orig_data:

                        old_value = self.orig_data[field_name]

                        # compare datetimes properly, regardless of whether they're offset-naive or offset-aware
                        if isinstance(value, datetime.datetime) and isinstance(old_value, datetime.datetime):
                            value = value.replace(tzinfo=None) + (value.utcoffset() or datetime.timedelta(seconds=0))
                            old_value = old_value.replace(tzinfo=None) + (old_value.utcoffset() or datetime.timedelta(seconds=0))

                        if value != old_value:
                            raise ValidationError('Value cannot be changed.')

                    self.data[field_name] = value

            except ValidationError as e:
                self.field_errors[raw_field_name] = e.args and e.args[0]
            except StopValidation as e:
                self.data[field_name] = e.args and e.args[0]

        try:
            self.clean()
        except ValidationError as e:
            self.errors = [e.args and e.args[0]]

        self.raise_on_errors()
        return self.data

    def raise_on_errors(self):
        if self.field_errors or self.errors:
            raise ValidationError({
                'field-errors': self.field_errors,
                'errors': self.errors,
            })

    def external_clean(self, cls, raise_on_errors=True):
        try:
            # Instantiate the external schema with the right raw_data/data.
            external_schema = cls(raw_data=self.raw_data, data=self.data)

            # Make sure its orig_data is the same as this schema's
            external_schema.orig_data = self.orig_data

            # Validate the schema and update self.data with its results.
            self.data.update(external_schema.full_clean())
        except ValidationError as e:
            self.field_errors.update(e.args[0]['field-errors'])
            self.errors += e.args[0]['errors']
            if raise_on_errors:
                self.raise_on_errors()

    def serialize(self):
        data = {}
        for field_name, field in self.fields.items():
            data[field_name] = field.serialize(self.data[field_name])
        return data
