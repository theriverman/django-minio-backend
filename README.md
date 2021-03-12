[![Actions Status](https://github.com/theriverman/django-minio-backend/workflows/publish-py-dist-to-pypi/badge.svg)](https://github.com/theriverman/django-minio-backend/actions)
[![PYPI](https://img.shields.io/pypi/v/django-minio-backend.svg)](https://pypi.python.org/pypi/django-minio-backend)

# django-minio-backend
The **django-minio-backend** provides a wrapper around the 
[MinIO Python SDK](https://docs.min.io/docs/python-client-quickstart-guide.html).
See [minio/minio-py](https://github.com/minio/minio-py) for the source.

## Integration
1. Get and install the package:
```bash
pip install django-minio-backend
```

2. Add `django_minio_backend` to `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # '...'
    'django_minio_backend',  # https://github.com/theriverman/django-minio-backend
]
```

If you would like to enable on-start consistency check, install via `DjangoMinioBackendConfig`:
```python
INSTALLED_APPS = [
    # '...'
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
  * Django 2.2 or later
  * Python 3.6.0 or later
  * MinIO SDK 7.0.2 or later

**Note:** This library relies heavily on [PEP 484 -- Type Hints](https://www.python.org/dev/peps/pep-0484/) 
which was introduced in *Python 3.5.0*.

## Contribution
Please find the details in [CONTRIBUTE.md](CONTRIBUTE.md)

## Copyright
  * theriverman/django-minio-backend licensed under the MIT License
  * minio/minio-py is licensed under the Apache License 2.0
