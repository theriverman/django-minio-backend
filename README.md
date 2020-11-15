[![Board Status](https://dev.azure.com/kristofdaja/ce976b79-9da3-4e26-a128-0e9471858160/0d69c064-41f3-4a98-9c49-1623149803d9/_apis/work/boardbadge/4fbdd57f-fc00-4dd6-8f2f-a1ced6cfbb10)](https://dev.azure.com/kristofdaja/ce976b79-9da3-4e26-a128-0e9471858160/_boards/board/t/0d69c064-41f3-4a98-9c49-1623149803d9/Microsoft.RequirementCategory)
[![Build Status](https://travis-ci.org/theriverman/django-minio-backend.svg?branch=master)](https://travis-ci.org/theriverman/django-minio-backend)

# django-minio-backend
The **django-minio-backend** provides a wrapper around the 
[MinIO Python SDK](https://docs.min.io/docs/python-client-quickstart-guide.html).

## Integration
1. Get and install the package:
```bash
pip install django-minio-backend
```

2. Add `django_minio_backend` to `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    '...'
    'django_minio_backend',  # https://github.com/theriverman/django-minio-backend
]
```

If you would like to enable on-start consistency check, install via `DjangoMinioBackendConfig`:
```python
INSTALLED_APPS = [
    '...'
    'django_minio_backend.apps.DjangoMinioBackendConfig',  # https://github.com/theriverman/django-minio-backend
]
``` 
Then add the following parameter to your settings file:
```python
MINIO_CONSISTENCY_CHECK_ON_START = True
```

**Note:** The on-start consistency check equals to manually calling `python manage.py initialize_buckets`. <br>
It is recommended to turn *off* this feature during development by setting `MINIO_CONSISTENCY_CHECK_ON_START` to `False`, 
because this operation can noticeably slow down Django's boot time when many buckets are configured.

3. Add the following parameters to your `settings.py`:
```python
from datetime import timedelta
from typing import List, Tuple

MINIO_ENDPOINT = 'minio.your-company.co.uk'
MINIO_ACCESS_KEY = 'yourMinioAccessKey'
MINIO_SECRET_KEY = 'yourVeryS3cr3tP4ssw0rd'
MINIO_USE_HTTPS = True
MINIO_URL_EXPIRY_HOURS = timedelta(days=1)  # Default is 7 days (longest) if not defined
MINIO_CONSISTENCY_CHECK_ON_START = True
MINIO_PRIVATE_BUCKETS = [
    'django-backend-dev-private',
]
MINIO_PUBLIC_BUCKETS = [
    'django-backend-dev-public',
]
MINIO_POLICY_HOOKS: List[Tuple[str, dict]] = []
```

4. Implement your own Attachment handler and integrate **django-minio-backend**:
```python
from django.db import models
from django_minio_backend import MinioBackend, iso_date_prefix

class PrivateAttachment(models.Model):   
    file = models.FileField(verbose_name="Object Upload",
                            storage=MinioBackend(bucket_name='django-backend-dev-private'),
                            upload_to=iso_date_prefix)
```

5. Initialize the buckets & set their public policy (OPTIONAL):<br>
This `django-admin` command creates both the private and public buckets in case one of them does not exists,
and sets the *public* bucket's privacy policy from `private`(default) to `public`.<br>
```bash
python manage.py initialize_buckets
```

Code reference: [initialize_buckets.py](django_minio_backend/management/commands/initialize_buckets.py).

### Health Check
To check the connection link between Django and MinIO, use the provided `MinioBackend.is_minio_available()` method.<br>
It returns a `MinioServerStatus` instance which can be quickly evaluated as boolean.<br>

**Example:**
```python
from django_minio_backend import MinioBackend

minio_available = MinioBackend('').is_minio_available()  # An empty string is fine this time
if minio_available:
    print("OK")
else:
    print("NOK")
    print(minio_available.details)
```

### Policy Hooks
You can configure **django-minio-backend** to automatically execute a set of pre-defined policy hooks. <br>
Policy hooks can be defined in `settings.py` by adding `MINIO_POLICY_HOOKS` which must be a list of tuples. <br>
Policy hooks are automatically picked up by the `initialize_buckets` management command.

For an exemplary policy, see the implementation of `def set_bucket_to_public(self)` 
in [django_minio_backend/models.py](django_minio_backend/models.py) or the contents 
of [examples/policy_hook.example.py](examples/policy_hook.example.py).

### Consistency Check On Start
When enabled, the `initialize_buckets` management command gets called automatically when Django starts. <br>
This command connects to the configured minIO server and checks if all buckets defined in `settings.py`. <br>
In case a bucket is missing or its configuration differs, it gets created and corrected.

### Reference Implementation
For a reference implementation, see [Examples](examples).

## Compatibility
  * Django 2.0 or later
  * Python 3.6.0 or later

**Note:** This library relies heavily on [PEP 484 -- Type Hints](https://www.python.org/dev/peps/pep-0484/) 
which was introduced in *Python 3.5.0*.

## Contribution
To build a new package, execute the following command:
`python setup.py sdist`

## Local Test Environment
To setup your local test environment, execute the following steps:
1. Clone the repository
```bash
git clone git@github.com:theriverman/django-minio-backend.git
```
2. Move to `example_app`:
```bash
cd django-minio-backend/example_app
```
3. Create the virtual environment:
```bash
pipenv install --dev
```
**Note:** On Windows, you might be required to move to the parent directory (`cd ..`) and execute the above command there.
3. Activate the virtual environment (if not active yet):
```bash
pipenv shell
```
4. Apply migrations:
```bash
python manage.py migrate
```
5. Start Django
```bash
python manage.py runserver
```

## Copyright
  * theriverman/django-minio-backend licensed under the MIT License
  * minio/minio-py is licensed under the Apache License 2.0
