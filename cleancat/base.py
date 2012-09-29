import re

class ValidationError(Exception):
    pass

class StopValidation(Exception):
    pass

class Field(object):
    base_type = None
    blank_value = None

    def __init__(self, required=True, default=None):
        self.required = required
        self.default = default

    def has_value(self, value):
        return value is not None

    def clean(self, value):
        if self.base_type is not None and value is not None and not isinstance(value, self.base_type):
            raise ValidationError('Value must be of %s type.' % self.base_type)

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

    def has_value(self, value):
        return bool(value)

class Bool(Field):
    base_type = bool
    blank_value = False

class Regex(String):
    regex = None
    regex_flags = 0
    regex_message = u'Invalid input.'

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

class Email(Regex):
    regex = r'^.+@[^.].*\.[a-z]{2,10}$'
    regex_flags = re.IGNORECASE
    regex_message = u'Invalid email address.'

class Integer(Field):
    base_type = int

class List(Field):
    base_type = list
    blank_value = []

    def __init__(self, field_instance, **kwargs):
        super(List, self).__init__(**kwargs)
        self.field_instance = field_instance

    def has_value(self, value):
        return bool(value)

    def clean(self, value):
        value = super(List, self).clean(value)
        if self.required and not len(value):
            raise ValidationError('List must not be empty.')

        return [self.field_instance.clean(item) for item in value]

class Embedded(Field):
    base_type = dict

    def __init__(self, schema_class, **kwargs):
        super(Embedded, self).__init__(**kwargs)
        self.schema_class = schema_class

    def has_value(self, value):
        return bool(value)

    def clean(self, value):
        value = super(Embedded, self).clean(value)

        return self.schema_class(value).full_clean()

    def is_valid(self):
        try:
            self.clean()
        except ValidationError:
            return False
        else:
            return True

class Choices(Field):
    def __init__(self, choices, **kwargs):
        super(Choices, self).__init__(**kwargs)
        self.choices = choices

    def get_choices(self):
        return self.choices

    def clean(self, value):
        value = super(Choices, self).clean(value)

        choices = self.get_choices()
        if value not in choices:
            raise ValidationError(u'Not a valid choice.')

        return value

# TODO move to separate module
class MongoReference(Field):
    base_type = basestring

    def __init__(self, document_class=None, **kwargs):
        self.document_class = document_class
        super(MongoReference, self).__init__(**kwargs)

    def clean(self, value):
        value = super(MongoReference, self).clean(value)
        try:
            return self.document_class.objects.get(pk=value)
        except self.document_class.DoesNotExist:
            raise ValidationError(u'Object does not exist.')

class Schema(object):
    def __init__(self, raw_data=None, data=None):
        self.raw_data = raw_data or {}
        self.orig_data = data or None
        self.data = data and data.copy() or {}
        self.errors = {}
        self.non_field_errors = []
        self.fields = {}

        for field in dir(self):
            if isinstance(getattr(self, field), Field):
                self.fields[field] = getattr(self, field)

    def clean(self):
        pass

    def full_clean(self):
        for field_name, field in self.fields.iteritems():
            try:
                # Treat non-existing fields like None.
                if field_name in self.raw_data or field_name not in self.data:
                    self.data[field_name] = field.clean(self.raw_data.get(field_name))

            except ValidationError, e:
                self.errors[field_name] = e.message
            except StopValidation, e:
                self.data[field_name] = e.message

        try:
            self.clean()
        except ValidationError, e:
            self.non_field_errors = [e.message]

        if self.errors or self.non_field_errors:
            raise ValidationError({
                'errors': self.errors,
                'non-field-errors': self.non_field_errors,
            })
        else:
            return self.data

    def external_clean(self, cls):
        try:
            self.data.update(cls(self.raw_data, self.data).full_clean())
        except ValidationError, e:
            self.errors.update(e.message['errors'])
            self.non_field_errors += e.message['non-field-errors']
            raise
