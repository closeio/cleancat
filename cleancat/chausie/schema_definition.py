import itertools
import typing
from typing import Dict, Any, Union

import attr

from cleancat.chausie.consts import empty, omitted
from cleancat.chausie.field import Field, ValidationError, Value, Errors


@attr.frozen
class SchemaDefinition:
    fields: Dict[str, Field]


def clean(
    schema_definition: SchemaDefinition, data: Any, context: Any = empty
) -> Union[Dict[str, Any], ValidationError]:
    """Entrypoint for cleaning some set of data for a given schema definition."""
    field_defs = [
        (name, f_def) for name, f_def in schema_definition.fields.items()
    ]

    # fake an initial 'self' result so function-defined fields can
    # optionally include an unused "self" parameter
    results: Dict[str, Union[Value, Errors]] = {"self": Value(value=None)}

    # initial set are those with met deps
    eval_queue: typing.List[typing.Tuple[str, Field]] = []
    delayed_eval = []
    for name, f in field_defs:
        if not f.depends_on or all([d in results for d in f.depends_on]):
            eval_queue.append((name, f))
        else:
            delayed_eval.append((name, f))
    assert len(field_defs) == len(eval_queue) + len(delayed_eval)

    while eval_queue:
        field_name, field_def = eval_queue.pop()

        accepts = field_def.accepts or (field_name,)
        value = empty
        for accept in accepts:
            value = getter(data, accept, omitted)
            if value is not omitted:
                break
        assert value is not empty

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
                        (dep in results and isinstance(results[dep], Value))
                        for dep in f.depends_on
                    ]
                )
            ):
                eval_queue.append((name, f))

    errors = list(
        itertools.chain(
            *[
                v.flatten()
                for v in results.values()
                if not isinstance(v, Value)
            ]
        )
    )
    if errors:
        return ValidationError(errors=errors)

    # we already checked for errors above, but this extra explicit check
    # helps mypy figure out what's going on.
    validated_values = {
        k: v.value
        for k, v in results.items()
        if isinstance(v, Value) and k != "self"
    }
    assert set(validated_values.keys()) == {f_name for f_name, _ in field_defs}
    return validated_values


def serialize(
    schema_definition: SchemaDefinition, data: Dict[str, Any]
) -> Dict:
    """Serialize a schema to a dictionary, respecting serialization settings."""
    result = {
        (field_def.serialize_to or field_name): field_def.serialize_func(
            data[field_name]
        )
        for field_name, field_def in schema_definition.fields.items()
    }
    return {k:v for k, v in result.items() if v is not omitted}


def getter(dict_or_obj, field_name, default):
    if isinstance(dict_or_obj, dict):
        return dict_or_obj.get(field_name, default)
    else:
        getattr(dict_or_obj, field_name, default)
