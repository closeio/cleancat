import typing
from typing import Dict, TypeVar, Callable, Type, Any, Union

from cleancat.chausie.consts import omitted, empty
from cleancat.chausie.field import Field, FIELD_TYPE_MAP, ValidationError, Error, Value, simple_field, Optional as CCOptional


def getter(dict_or_obj, field, default):
    if isinstance(dict_or_obj, dict):
        return dict_or_obj.get(field, omitted)
    else:
        getattr(dict_or_obj, field, omitted)


SchemaCls = TypeVar('SchemaCls')


def get_fields(cls: SchemaCls) -> Dict[str, Callable]:
    return {
        field_name: field_def
        for field_name, field_def in cls.__dict__.items()
        if isinstance(field_def, Field)
    }


def schema(cls: SchemaCls, getter=getter, autodef=True):
    """
    Annotate a class to turn it into a schema.

    Args:
        getter: given an object + field name, gets the value from the obj
        autodef: automatically define simple fields for annotated attributes
    """
    # auto define simple annotations
    if autodef:

        def _field_def_from_annotation(annotation):
            if annotation in FIELD_TYPE_MAP:
                return simple_field(parents=(FIELD_TYPE_MAP[annotation],))
            elif typing.get_origin(annotation) is Union:
                # basic support for `Optional`
                union_of = typing.get_args(annotation)
                if not (len(union_of) == 2 and type(None) in union_of):
                    raise TypeError('Unrecognized type annotation.')

                inner = next(
                    t
                    for t in typing.get_args(annotation)
                    if t is not type(None)
                )
                if inner in FIELD_TYPE_MAP:
                    return simple_field(
                        parents=(FIELD_TYPE_MAP[inner],),
                        nullability=CCOptional(),
                    )

            raise TypeError('Unrecognized type annotation.')

        existing_fields = get_fields(cls)
        for field, f_type in getattr(cls, '__annotations__', {}).items():
            if field not in existing_fields:
                setattr(cls, field, _field_def_from_annotation(f_type))

    # check for dependency loops
    # TODO

    def _clean(data: Any, context: Any) -> Union[SchemaCls, ValidationError]:
        field_defs = [(name, f_def) for name, f_def in get_fields(cls).items()]

        # initial set are those with no
        eval_queue = []
        delayed_eval = []
        for name, f in field_defs:
            if f.depends_on:
                delayed_eval.append((name, f))
            else:
                eval_queue.append((name, f))
        assert len(field_defs) == len(eval_queue) + len(delayed_eval)

        results: Dict[str, Union[Value, Error]] = {}
        while eval_queue:
            field_name, field_def = eval_queue.pop()

            accepts = field_def.accepts or (field_name,)
            for accept in accepts:
                value = getter(data, accept, omitted)
                if value is not omitted:
                    break

            results[field_name] = field_def.run_validators(
                field=(field_name,),
                value=value,
                context=context,
                intermediate_results=results,
            )
            queued_fields = {n for n, _f in eval_queue}
            for name, f in delayed_eval:
                if (
                        name not in results
                        and name not in queued_fields
                        and all(
                    [
                        (
                                dep in results
                                and not isinstance(results[dep], Error)
                        )
                        for dep in f.depends_on
                    ]
                )
                ):
                    eval_queue.append((name, f))

        errors = {f: v for f, v in results.items() if isinstance(v, Error)}
        if errors:
            return ValidationError(errors=list(errors.values()))

        return cls(**results)

    cls.__clean = _clean

    def _new_init(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v.value)

    cls.__init__ = _new_init

    def _serialize(self):
        # very simple serialize
        return {
            field_def.serialize_to
            or field_name: (
                field_def.serialize_func(getattr(self, field_name))
            )
            for field_name, field_def in get_fields(cls).items()
        }

    cls.__serialize = _serialize

    return cls


def clean(
        schema: Type[SchemaCls], data: Any, context: Any = empty
) -> SchemaCls:
    return schema.__clean(data=data, context=context)


def serialize(schema: SchemaCls) -> Dict:
    return schema.__serialize()
