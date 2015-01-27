cleancat
========

Validation library for Python designed to be used with JSON REST frameworks


### Basic example in Flask

```
class JobApplication(Schema):
    first_name = String()
    last_name = String()
    email = Email()
    urls = List(URL(default_scheme='http://'))

@app.route('/job_application', methods=['POST'])
@mimerender(default='json', json=render_json)
def test_view():
    schema = JobApplication(request.json)
    try:
        data = schema.full_clean()
    except SchemaValidationError:
        return {'field-errors': schema.field_errors, 'errors': schema.errors }, '400 Bad Request'
        
    # Now "data" has the validated data
```
