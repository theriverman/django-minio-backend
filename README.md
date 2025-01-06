[![django-app-tests](https://github.com/theriverman/django-minio-backend/actions/workflows/django-tests.yml/badge.svg)](https://github.com/theriverman/django-minio-backend/actions/workflows/django-tests.yml)
[![publish-py-dist-to-pypi](https://github.com/theriverman/django-minio-backend/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/theriverman/django-minio-backend/actions/workflows/publish-to-pypi.yml)
[![PYPI](https://img.shields.io/pypi/v/django-minio-backend.svg)](https://pypi.python.org/pypi/django-minio-backend)

# django-minio-backend
The **django-minio-backend** provides a wrapper around the 
[MinIO Python SDK](https://docs.min.io/docs/python-client-quickstart-guide.html).
See [minio/minio-py](https://github.com/minio/minio-py) for the source.

## Requirements & Compatibility
  * Django 4.2 or later
  * Python 3.11.0 or later
  * MinIO SDK 7.2.8 or later (installed automatically)

## What's in the box?
The following set of features are available in **django-minio-backend**:
* Django File Storage System Integration
  * Compliance with the `django.core.files.storage.Storage` class
  * Static Files Support
* Utilise/manage private and public buckets
  * Create buckets with custom policy hooks (`MINIO_POLICY_HOOKS`)
  * Consistency Check on Start (`MINIO_CONSISTENCY_CHECK_ON_START`)
  * Bucket Check on Upload (`MINIO_BUCKET_CHECK_ON_SAVE`)
* Health Check (`MinioBackend.is_minio_available()`)
* Docker Networking Support
* Management Commands:
  * initialize_buckets
  * is_minio_available
* Support for multiple MinIO backends via separate `settings.py` entries

## Integration
1. Get and install the package:
    ```bash
    pip install django-minio-backend
    ```

2. Add `django_minio_backend.apps.DjangoMinioBackendConfig` to `INSTALLED_APPS`:
    ```python
    INSTALLED_APPS = [
        # '...'
        'django_minio_backend.apps.DjangoMinioBackendConfig',  # https://github.com/theriverman/django-minio-backend
    ]
    ``` 

3. Add the following parameters to your `settings.py`:
    ```python
    from datetime import timedelta
    
    STORAGES = {  # -- ADDED in Django 5.1
        "staticfiles": {
            "BACKEND": "django_minio_backend.models.MinioBackendStatic",
            "OPTIONS": {
                "MINIO_ENDPOINT": "play.min.io",
                "MINIO_ACCESS_KEY": "Q3AM3UQ867SPQQA43P2F",
                "MINIO_SECRET_KEY": "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                "MINIO_USE_HTTPS": True,
                "MINIO_REGION": "us-east-1",
                "MINIO_URL_EXPIRY_HOURS": timedelta(days=1),  # Default is 7 days (longest) if not defined
                "MINIO_CONSISTENCY_CHECK_ON_START": True,
                "MINIO_STATIC_FILES_BUCKET": "my-static-files-bucket",
            },
        },
        "default": {
            "BACKEND": "django_minio_backend.models.MinioBackend",
            "OPTIONS": {
                "MINIO_ENDPOINT": "play.min.io",
                "MINIO_EXTERNAL_ENDPOINT": "external.min.io",
                "MINIO_EXTERNAL_ENDPOINT_USE_HTTPS": True,
                "MINIO_ACCESS_KEY": "Q3AM3UQ867SPQQA43P2F",
                "MINIO_SECRET_KEY": "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                "MINIO_USE_HTTPS": True,
                "MINIO_REGION": "us-east-1",
                "MINIO_PRIVATE_BUCKETS": ['django-backend-dev-private', 'my-media-files-bucket', ],
                "MINIO_PUBLIC_BUCKETS": ['django-backend-dev-public', 't5p2g08k31', '7xi7lx9rjh' ],
                "MINIO_URL_EXPIRY_HOURS": timedelta(days=1),  # Default is 7 days (longest) if not defined
                "MINIO_CONSISTENCY_CHECK_ON_START": False,
                "MINIO_POLICY_HOOKS": [  # List[Tuple[str, dict]]
                    # ('django-backend-dev-private', dummy_policy)
                ],
                "MINIO_DEFAULT_BUCKET": "my-media-files-bucket",
                "MINIO_STATIC_FILES_BUCKET": "my-static-files-bucket",
                "MINIO_BUCKET_CHECK_ON_SAVE": False,
            },
        },
    }
    
    # Custom HTTP Client (OPTIONAL)
    import os
    import certifi
    import urllib3
    timeout = timedelta(minutes=5).seconds
    ca_certs = os.environ.get('SSL_CERT_FILE') or certifi.where()
    STORAGES["default"]["OPTIONS"]["MINIO_HTTP_CLIENT"]: urllib3.poolmanager.PoolManager
    STORAGES["default"]["OPTIONS"]["MINIO_HTTP_CLIENT"] = urllib3.PoolManager(
        timeout=urllib3.util.Timeout(connect=timeout, read=timeout),
        maxsize=10,
        cert_reqs='CERT_REQUIRED',
        ca_certs=ca_certs,
        retries=urllib3.Retry(
            total=5,
            backoff_factor=0.2,
            status_forcelist=[500, 502, 503, 504]
        )
    )
    ```

4. Implement your own lazy-loaded Attachment handler and integrate **django-minio-backend**:
    ```python
    # storages.py
    from django_minio_backend.models import MinioBackend

    def get_public_storage():
        return MinioBackend(
            bucket_name='django-backend-dev-public',
            storage_name='default',
        )
    
    def get_private_storage():
        return MinioBackend(
            bucket_name='django-backend-dev-private',
            storage_name='default',
        )
    ```
   
    ```python
    # models.py
    from django.db import models
    from django_minio_backend import MinioBackend, iso_date_prefix
    from .storages import get_public_storage, get_private_storage
    
    class PrivateAttachment(models.Model):   
        file: FieldFile = models.FileField(verbose_name="Object Upload",
                                           storage=get_private_storage, upload_to=set_file_path_name)
    ```
    **Note:** It is highly recommended to declare your `MinioBackend` class instances in a callable function to avoid
    future Django migration problems due to Django's model serialization.

5. Initialize the buckets & set their public policy (OPTIONAL):<br>
This `django-admin` command creates both the private and public buckets in case one of them does not exist,
and sets the *public* bucket's privacy policy from `private`(default) to `public`.<br>
    ```bash
    python manage.py initialize_buckets
    ```

    Code reference: [initialize_buckets.py](django_minio_backend/management/commands/initialize_buckets.py).

### Static Files Support
**django-minio-backend** allows serving static files from MinIO.
To learn more about Django static files, see [Managing static files](https://docs.djangoproject.com/en/5.1/howto/static-files/), [STATICFILES_STORAGE](https://docs.djangoproject.com/en/5.1/ref/settings/#static-files) and [STORAGES](https://docs.djangoproject.com/en/5.1/ref/settings/#std-setting-STORAGES).

To enable static files support, update your `settings.py`:
```python
STORAGES = {  # -- ADDED IN Django 5.1
    "default": {
        "BACKEND": "django_minio_backend.models.MinioBackend",
    },
    "staticfiles": {  # -- ADD THESE LINES FOR STATIC FILES SUPPORT
        "BACKEND": "django_minio_backend.models.MinioBackendStatic",
        "OPTIONS": {
            "MINIO_ENDPOINT": "play.min.io",  # ONLY EXTERNAL ADDRESS FOR STATIC
            "MINIO_ACCESS_KEY": "Q3AM3UQ867SPQQA43P2F",
            "MINIO_SECRET_KEY": "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
            "MINIO_USE_HTTPS": False,
            "MINIO_REGION": "us-east-1",
            "MINIO_URL_EXPIRY_HOURS": timedelta(days=1),  # Default is 7 days (longest) if not defined
            "MINIO_CONSISTENCY_CHECK_ON_START": True,
            "MINIO_STATIC_FILES_BUCKET": "my-static-files-bucket",
        },
    },
}
```
The value of `STATIC_URL` is ignored, but it must be defined otherwise Django will throw an error.

**IMPORTANT**<br>
The bucket configured in `MINIO_STATIC_FILES_BUCKET` is forced to be public to avoid known Django errors. It is not supported to serve Django static files from a private bucket. 

**Note:** If `MINIO_STATIC_FILES_BUCKET` is not set, the default value (`auto-generated-bucket-static-files`) will be used.

### Default File Storage Support
**django-minio-backend** can be configured as a default file storage.
To learn more, see [STORAGES](https://docs.djangoproject.com/en/5.1/ref/settings/#std-setting-STORAGES).

To configure **django-minio-backend** as the default file storage, update `settings.py` with `MINIO_DEFAULT_BUCKET`:
```python
STORAGES = {  # -- ADDED IN Django 5.1
    "default": {
        "BACKEND": "django_minio_backend.models.MinioBackend",
        "OPTIONS": {
            # ...
            "MINIO_DEFAULT_BUCKET": "django-minio-backend-default-dev-bucket",  # PRIVATE by default if not declared below
            "MINIO_PRIVATE_BUCKETS": [ ],
            "MINIO_PUBLIC_BUCKETS": ['django-minio-backend-default-dev-bucket'],
            # ...
        },
    },
}
```

**IMPORTANT**<br>
The value set in `MINIO_DEFAULT_BUCKET` can be added either to `MINIO_PRIVATE_BUCKETS` or `MINIO_PUBLIC_BUCKETS`.
By default, **django-minio-backend** will register `MINIO_DEFAULT_BUCKET` as private.

**Note:** If `MINIO_DEFAULT_BUCKET` is not set, the default value (`auto-generated-bucket-media-files`) will be used.
Policy setting for default buckets is **private**.

### Health Check
To check the connection link between Django and MinIO, use the provided `MinioBackend.is_minio_available()` method.<br>
It returns a `MinioServerStatus` instance which can be quickly evaluated as boolean.<br>

**Example:**
```python
from django_minio_backend import MinioBackend

minio_available = MinioBackend().is_minio_available()  # An empty string is fine this time
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

For an exemplary policy, see the implementation of `set_bucket_to_public()` 
in [django_minio_backend/models.py](django_minio_backend/models.py) or the contents 
of [examples/policy_hook.example.py](examples/policy_hook.example.py).

### Consistency Check On Start
When enabled, the `initialize_buckets` management command gets called automatically when Django starts. <br>
This command connects to the configured MinIO server and checks if all buckets defined in `settings.py`. <br>
In case a bucket is missing or its configuration differs, it gets created and corrected.

**Note:** The on-start consistency check equals to manually calling `python manage.py initialize_buckets`. <br>
It is recommended to turn *off* this feature during development by setting `MINIO_CONSISTENCY_CHECK_ON_START` to `False`, 
because this operation can noticeably slow down Django's boot time when many buckets are configured.

### Reference Implementation
For a reference implementation, see [Examples](examples).

## Behaviour
The following list summarises the key characteristics of **django-minio-backend**:
  * STORAGES introduced in Django 5.1 enables configuring multiple storage backends with great customisation.
    * MEDIA and STATIC files must be configured separate and the latter must be named `staticfiles` explicitly.
    * STATIC files are stored in a single bucket managed via `MINIO_STATIC_FILES_BUCKET`.
    * STATIC files are **public** by default and must remain public to avoid certain Django admin errors.
    * The value of `MEDIA_URL` is ignored, but it must be defined otherwise Django will throw an error.
  * Bucket existence is **not** checked on a save by default.
    To enable this guard, set `MINIO_BUCKET_CHECK_ON_SAVE = True` in your `settings.py`.
  * Bucket existences are **not** checked on Django start by default.
    To enable this guard, set `MINIO_CONSISTENCY_CHECK_ON_START = True` in your `settings.py`.
  * Many configuration errors are validated through `AppConfig` but not every error can be captured there.
  * Files with the same name in the same bucket are **not** replaced on save by default. Django will store the newer file with an altered file name
    To allow replacing existing files, pass the `replace_existing=True` kwarg to `MinioBackend`.
    For example:
    ```python
    image = models.ImageField(storage=MinioBackend(bucket_name='images-public', storage_name="default",  replace_existing=True))
    ```
  * Depending on your configuration, **django-minio-backend** may communicate over two kind of interfaces: internal and external.
    If your `settings.py` defines a different value for `MINIO_ENDPOINT` and `MINIO_EXTERNAL_ENDPOINT`, then the former will be used for internal communication
    between Django and MinIO, and the latter for generating URLs for users. This behaviour optimises the network communication.
    See **Networking** below for a thorough explanation
  * The uploaded object's content-type is guessed during save. If `mimetypes.guess_type` fails to determine the correct content-type, then it falls back to `application/octet-stream`.

## Networking and Docker
If your Django application is running on a shared host with your MinIO instance, you should consider using the `MINIO_EXTERNAL_ENDPOINT` and `MINIO_EXTERNAL_ENDPOINT_USE_HTTPS` parameters.
This way most traffic will happen internally between Django and MinIO. The external endpoint parameters are required for external pre-signed URL generation.

If your Django application and MinIO instance are running on different hosts, you can omit the `MINIO_EXTERNAL_ENDPOINT` and `MINIO_EXTERNAL_ENDPOINT_USE_HTTPS` parameters, 
and **django-minio-backend** will default to the value of `MINIO_ENDPOINT`.

Setting up and configuring custom networks in Docker is not in the scope of this document. <br>
To learn more about Docker networking, see [Networking overview](https://docs.docker.com/network/) and [Networking in Compose](https://docs.docker.com/compose/networking/).

See [README.Docker.md](README.Docker.md) for a real-life Docker Compose demonstration.

## Contribution
Please find the details in [CONTRIBUTE.md](CONTRIBUTE.md)

## Copyright
  * theriverman/django-minio-backend licensed under the MIT License
  * minio/minio-py is licensed under the Apache License 2.0
