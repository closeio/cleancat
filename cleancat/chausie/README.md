CleanChausie
========

Data validation and transformation library for Python. Successor to CleanCat.

Key features:
* Operate on/with type-checked objects that have good IDE/autocomplete support
* Annotation-based declarations for simple fields
* Composable/reusable fields and field validation logic
* Support (but not require) passing around a context (to avoid global state)
  - Context pattern is compatible with explicit sqlalchemy-based session management. i.e. pass in a session when validating
* Cleanly support intra-schema field dependencies (i.e. one field can depend on the validated value of another)
* Explicit nullability/omission parameters
* Errors returned for multiple fields at a time, with field attribution

## CleanChausie By Example

### Basic example in Flask

This is a direct port of the example from the OG cleancat README.

This shows:
* Annotation-based declarations for simple fields.
* Type-checked objects (successful validation results in initialized instances of the schema)

```python
from typing import List
from cleancat.chausie.field import (
  field, emailfield, listfield, urlfield, ValidationError,
)
from cleancat.chausie.schema import Schema
from flask import app, request, jsonify

class JobApplication(Schema):
    first_name: str
    last_name: str
    email: str = field(emailfield())
    urls: List[str] = field(listfield(urlfield(default_scheme='http://')))

@app.route('/job_application', methods=['POST'])
def test_view():
    result = JobApplication.clean(request.json)
    if isinstance(result, ValidationError):
        return jsonify({'errors': [{'msg': e.msg, 'field': e.field} for e in result.errors] }), 400

    # Now "result" has the validated data, in the form of a `JobApplication` instance.
    assert isinstance(result, JobApplication)
    name = f'{result.first_name} {result.last_name}'
```

### Explicit Nullability

TODO revisit omission defaults so that they match the annotation

```python
from typing import Optional, Union
from cleancat.chausie.consts import OMITTED
from cleancat.chausie.field import field, strfield, Optional as CCOptional, Required
from cleancat.chausie.schema import Schema

class NullabilityExample(Schema):
  # auto defined based on annotations
  nonnull_required: str
  nullable_omittable: Optional[str]
  
  # manually specified
  nonnull_omittable: Union[str, OMITTED] = field(strfield, nullability=CCOptional(allow_none=False))
  nullable_required: Optional[str] = field(strfield, nullability=Required(allow_none=True))
```

### Composable/Reusable Fields

```python
from typing import Union
from cleancat.chausie.field import field, Field, strfield, intfield, Error
from cleancat.chausie.schema import Schema

@field(parents=(strfield,))
def trimmed_string(value: str) -> str:
    return value.strip()

def max_val(max_value: int) -> Field:
    @field()
    def _max_val(value: int) -> Union[int, Error]:
        if value > max_value:
            return Error(msg=f'value is above allowed max of {max_value}')
        return value
    return _max_val

def min_val(min_value: int) -> Field:
    @field()
    def _min_val(value: int) -> Union[int, Error]:
        if value < min_value:
            return Error(msg=f'value is below allowed min of {min_value}')
        return value
    return _min_val

def constrained_int(min: int, max: int) -> Field:
    return field(parents=(intfield, min_val(min), max_val(max)))()

class ReusableFieldsExampleSchema(Schema):
    first_name: str = trimmed_string
    age: int = field(parents=(intfield, min_val(0)))()
    score: int = constrained_int(min=0, max=100)
```

### Context Support

```python
import attrs
from cleancat.chausie.field import field, strfield
from cleancat.chausie.schema import Schema

class MyModel:  # some ORM model
    id: str
    created_by: 'User'

@attrs.frozen
class Context:
    authenticated_user: 'User'  # the User making a request
    session: 'Session'  # active ORM Session

class ContextExampleSchema(Schema):
    @field(parents=(strfield,), accepts=('id',))
    def obj(self, value: str, context: Context) -> MyModel:
        return (
            context.session
            .query(MyModel)
            .filter(MyModel.created_by == context.authenticated_user.id)
            .filter(MyModel.id == value)
        )

with atomic() as session:
    result = ContextExampleSchema.clean(
        data={'id': 'mymodel_primarykey'},
        context=Context(authenticated_user=EXAMPLE_USER, session=session)
    )
assert isinstance(result, ContextExampleSchema)
assert isinstance(result.obj, MyModel)
```


### Intra-schema Field dependencies

```python
from cleancat.chausie.field import field
from cleancat.chausie.schema import Schema

class DependencyExampleSchema(Schema):
    a: str
    b: str
    
    @field()
    def a_and_b(self, a: str, b: str) -> str:
        return f'{a}::{b}'


result = DependencyExampleSchema.clean(
  data={'a': 'a', 'b': 'b'},
)
assert isinstance(result, DependencyExampleSchema)
assert result.a_and_b == 'a::b'
```

### Per-Field Errors
