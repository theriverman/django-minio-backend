# django-minio-backend
The `django-minio-backend` provides a wrapper around the 
[MinIO Python Library](https://docs.min.io/docs/python-client-quickstart-guide.html).

## Integration
1. Get and install the package:
    `pip install django-minio-backend`

2. Add `django_minio_backend` to `INSTALLED_APPS`:
    ```python
    INSTALLED_APPS = [
        '...'
        'django_minio_backend',  # django-minio-backend | https://github.com/theriverman/django-minio-backend
    ]
    ```

3. Add the following parameters to your `settings.py`:
    ```python
    from datetime import timedelta
    MINIO_ENDPOINT = 'minio.yourcompany.co.uk'
    MINIO_ACCESS_KEY = 'yourMinioAccessKey'
    MINIO_SECRET_KEY = 'yourVeryS3cr3tP4ssw0rd'
    MINIO_USE_HTTPS = True
    MINIO_PRIVATE_BUCKET_NAME = 'my-app-private'
    MINIO_PUBLIC_BUCKET_NAME = 'my-app-public'
    MINIO_URL_EXPIRY_HOURS = timedelta(days=1)
    ```

4. Implement your own Attachment handler and integrate django-minio-backend:
    ```python
    from django.db import models
    from django_minio_backend import MinioBackend, iso_date_prefix
    
    # noinspection PyUnresolvedReferences
    class PrivateAttachment(models.Model):   
        file = models.FileField(verbose_name="Object Upload", storage=MinioBackend(is_public=False),
                                upload_to=iso_date_prefix)
    ```

5. Initialize buckets & set public policy (OPTIONAL):<br>
    This `django-admin` command creates both the private and public buckets in case one of them does not exists
    and sets the public bucket's privacy policy from private(default) to public.<br>
    `python manage.py initialize_buckets`
    
    Code reference: [initialize_buckets.py](django_minio_backend/management/commands/initialize_buckets.py).


### Reference Implementation
For a reference implementation, see [Examples](examples).

## Compatibility
  * Django 2.0 or later
  * Python 3.5.0 or later
**Note:** This library relies heavily on [PEP 484 -- Type Hints](https://www.python.org/dev/peps/pep-0484/) 
which was introduced in *Python 3.5.0*.

## Contribution
To build a new package, execute the following command:
`python setup.py sdist`

## Copyright
theriverman/django-minio-backend licensed under the MIT License
minio/minio-py is licensed under the Apache License 2.0
