CleanCat
========

[![Build Status](https://travis-ci.org/closeio/cleancat.svg?branch=master)](https://travis-ci.org/closeio/cleancat)

Validation library for Python designed to be used with JSON REST frameworks


### Basic example in Flask

```py
class JobApplication(Schema):
    first_name = String()
    last_name = String()
    email = Email()
    urls = List(URL(default_scheme='http://'))

@app.route('/job_application', methods=['POST'])
def test_view():
    schema = JobApplication(request.json)
    try:
        data = schema.full_clean()
    except SchemaValidationError:
        return jsonify({'field-errors': schema.field_errors, 'errors': schema.errors }), 400
        
    # Now "data" has the validated data
```
