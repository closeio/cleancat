CleanChausie
========

Data validation and transformation library for Python. Successor to CleanCat.

Key features:
* 


### Basic example in Flask

```python
from cleancat.chausie import schema, field, ValidationError

@schema
class JobApplication:
    first_name: str
    last_name: str
    email: str = field(emailfield)
    urls: List[str] = field(listfield(urlfield(default_scheme='http://')))

@app.route('/job_application', methods=['POST'])
def test_view():
    result = clean(JobApplication, request.json)
    if isinstance(result, ValidationError):
        return jsonify({'errors': [{'msg': e.msg, 'field': e.field} for e in result.errors] }), 400

    # Now "result" has the validated data, in the form of a `JobApplication` instance.
    assert isinstance(result, JobApplication)
    name = f'{result.first_name} {result.last_name}'
```
