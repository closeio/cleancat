import datetime
import pytz
import re
import sys
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

    def __init__(self, required=True, default=None, field_name=None, raw_field_name=None, mutable=True):
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

    def has_value(self, value):
        return value is not None

    def clean(self, value):
        if self.base_type is not None and value is not None and not isinstance(value, self.base_type):
            raise ValidationError('Value must be of %s type.' % self.base_type.__name__)

        if not self.has_value(value):
            if self.default != None:
                raise StopValidation(self.default)

            if self.required:
                raise ValidationError('This field is required.')
            else:
                raise StopValidation(self.blank_value)

        return value

class String(Field):
    base_type = basestring
    blank_value = ''
    min_length = None
    max_length = None

    def __init__(self, min_length=None, max_length=None, **kwargs):
        if min_length != None:
            self.min_length = min_length
        if max_length != None:
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
        if regex != None:
            self.regex = regex
        if regex_flags != None:
            self.regex_flags = regex_flags
        if regex_message != None:
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

class Email(Regex):
    regex = r'^.+@[^.].*\.[a-z]{2,63}$'
    regex_flags = re.IGNORECASE
    regex_message = 'Invalid email address.'
    max_length = 254

class URL(Regex):
    blank_value = None

    def __init__(self, require_tld=True, default_scheme=None, allowed_schemes=None, **kwargs):
        tld_part = (require_tld and r'\.[a-z]{2,10}' or '')
        scheme_part = '[a-z]+://'
        self.default_scheme = default_scheme
        if self.default_scheme and not self.default_scheme.endswith('://'):
            self.default_scheme += '://'
        self.scheme_regex = re.compile('^'+scheme_part, re.IGNORECASE)
        if default_scheme:
            scheme_part = '(%s)?' % scheme_part
        regex = r'^%s([^/:]+%s|([0-9]{1,3}\.){3}[0-9]{1,3})(:[0-9]+)?(\/.*)?$' % (scheme_part, tld_part)
        super(URL, self).__init__(regex=regex, regex_flags=re.IGNORECASE, regex_message='Invalid URL.', **kwargs)

        self.allowed_schemes = allowed_schemes or []
        self.allowed_schemes_regexes = []
        for sch in self.allowed_schemes:
            if not sch.endswith('://'):
                sch += '://'
            self.allowed_schemes_regexes.append(re.compile('^'+sch+'.*', re.IGNORECASE))

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

class Choices(Field):
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

# TODO move to separate module
class MongoEmbedded(Embedded):
    """
    Represents an embedded document. Expects the document contents as input.
    Example document: EmbeddedDocumentField(Doc)
    """
    def __init__(self, document_class=None, *args, **kwargs):
        self.document_class = document_class
        super(MongoEmbedded, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(MongoEmbedded, self).clean(value)
        return self.document_class(**value)

class MongoEmbeddedReference(MongoEmbedded):
    """
    Represents a reference. Expects the document contents as input.
    Example document: ReferenceField(Doc)

    The primary key of the related reference can be specified using pk_field.
    By default, `id` is the pk_field. If the passed document contains the
    pk_field, it is validated whether a document with that ID exists. If the
    document does not contain the pk_field, it is assumed that a new document
    will be created.

    Examples:
    {'id': 'existing_id', 'foo': 'bar'} -> valid
    {'id': 'non-existing_id', 'foo': 'bar'} -> invalid
    {'foo': 'bar'} -> valid
    """
    def __init__(self, *args, **kwargs):
        self.pk_field = kwargs.pop('pk_field', 'id')
        super(MongoEmbeddedReference, self).__init__(*args, **kwargs)


    def clean(self, value):
        value = super(Embedded, self).clean(value)
        return self.schema_class(value).full_clean()

    def clean(self, value):
        from mongoengine import ValidationError as MongoValidationError
        if value and self.pk_field in value:
            try:
                document = self.document_class.objects.get(pk=value[self.pk_field])
            except self.document_class.DoesNotExist:
                raise ValidationError('Object does not exist.')
            except MongoValidationError as e:
                raise ValidationError(unicode(e))
            else:
                value = Dict.clean(self, value)
                if hasattr(document, 'to_dict'): # support mongomallard
                    document_data = document.to_dict()
                else:
                    document_data = document._data.copy()
                if None in document_data:
                    del document_data[None]
                value = self.schema_class(value, document_data).full_clean()
                for field_name, field_value in value.items():
                    if field_name != self.pk_field:
                        setattr(document, field_name, field_value)
                return document
        else:
            value = Dict.clean(self, value)
            value = self.schema_class(value).full_clean()
            return self.document_class(**value)

class MongoReference(Field):
    """
    Represents a reference. Expects the ID as input.
    Example document: ReferenceField(Doc)
    """

    base_type = basestring

    def __init__(self, document_class=None, **kwargs):
        self.document_class = document_class
        super(MongoReference, self).__init__(**kwargs)

    def clean(self, value):
        value = super(MongoReference, self).clean(value)
        try:
            return self.document_class.objects.get(pk=value)
        except self.document_class.DoesNotExist:
            raise ValidationError('Object does not exist.')

class Schema(object):
    def __init__(self, raw_data=None, data=None):
        conflicting_fields = set([
            'raw_data', 'orig_data', 'data', 'errors', 'field_errors', 'fields'
        ]).intersection(dir(self))
        if conflicting_fields:
            raise Exception('The following field names are reserved and need to be renamed: %s. '
                'Please use the field_name keyword to use them.' % list(conflicting_fields))

        self.raw_data = raw_data or {}
        self.orig_data = data or None
        self.data = data and data.copy() or {}
        self.field_errors = {}
        self.errors = []
        self.fields = {}

        for field_name in dir(self):
            if isinstance(getattr(self, field_name), Field):
                field = getattr(self, field_name)
                field_name = field.field_name or field_name
                self.fields[field_name] = field

    def clean(self):
        pass

    def full_clean(self):
        if not isinstance(self.raw_data, dict):
            raise ValidationError({
                'errors': [ 'Invalid request: JSON dictionary expected.' ]
            })

        for field_name, field in self.fields.items():
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
            self.data.update(cls(self.raw_data, self.data).full_clean())
        except ValidationError as e:
            self.field_errors.update(e.args[0]['field-errors'])
            self.errors += e.args[0]['errors']
            if raise_on_errors:
                self.raise_on_errors()
