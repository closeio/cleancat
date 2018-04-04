_schema_registry = {}


class SchemaNotRegistered(Exception):
    """Raised when we attempt to get a Schema by a name that hasn't been
    registered.
    """
    pass


def get_schema_by_name(schema_name):
    """Return a specific Schema class when given its name.

    For example, if you defined a BookSchema like so:

    class BookSchema(Schema):
        title = String()

    Then `get_schema_by_name('BookSchema')` should return the `BookSchema`
    class.
    """
    schema_cls = _schema_registry.get(schema_name)
    if schema_cls:
        return schema_cls

    raise SchemaNotRegistered(
        '{} has not been registered in the CleanCat schema registry.'.format(
            schema_name
        )
    )


def add_schema_to_registry(schema_name, schema_class):
    # XXX using just the name prevents us from having same-named schemas in
    # different modules.
    _schema_registry[schema_name] = schema_class
