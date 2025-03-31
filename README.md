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
  * clean_orphaned_minio_files
* URL Caching for improved performance

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
    
    STORAGES = {  # -- ADDED IN Django 5.1
        "default": {
            "BACKEND": "django_minio_backend.models.MinioBackend",
        },
        # "staticfiles": {  # -- OPTIONAL
        #     "BACKEND": "django_minio_backend.models.MinioBackendStatic",
        # },
    }
    
    MINIO_ENDPOINT = 'minio.your-company.co.uk'
    MINIO_EXTERNAL_ENDPOINT = "external-minio.your-company.co.uk"  # Default is same as MINIO_ENDPOINT
    MINIO_EXTERNAL_ENDPOINT_USE_HTTPS = True  # Default is same as MINIO_USE_HTTPS
    MINIO_REGION = 'us-east-1'  # Default is set to None
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
    # MINIO_MEDIA_FILES_BUCKET = 'my-media-files-bucket'  # replacement for MEDIA_ROOT
    # MINIO_STATIC_FILES_BUCKET = 'my-static-files-bucket'  # replacement for STATIC_ROOT
    MINIO_BUCKET_CHECK_ON_SAVE = True  # Default: True // Creates bucket if missing, then save
    MINIO_URL_CACHE_TIMEOUT = 60 * 60 * 8  # 8 hours in seconds, defaults to 80% of MINIO_URL_EXPIRY_HOURS
    MINIO_URL_CACHE_PREFIX = 'minio_url_'  # Prefix for cache keys to avoid collisions
    MINIO_URL_CACHING_ENABLED = False  # Enable/disable URL caching, defaults to False

    # Custom HTTP Client (OPTIONAL)
    import os
    import certifi
    import urllib3
    timeout = timedelta(minutes=5).seconds
    ca_certs = os.environ.get('SSL_CERT_FILE') or certifi.where()
    MINIO_HTTP_CLIENT: urllib3.poolmanager.PoolManager = urllib3.PoolManager(
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
    },
}
MINIO_STATIC_FILES_BUCKET = 'my-static-files-bucket'  # replacement for STATIC_ROOT
# Add the value of MINIO_STATIC_FILES_BUCKET to one of the pre-configured bucket lists. e.g.:
# MINIO_PRIVATE_BUCKETS.append(MINIO_STATIC_FILES_BUCKET)
# MINIO_PUBLIC_BUCKETS.append(MINIO_STATIC_FILES_BUCKET)
```

The value of `STATIC_URL` is ignored, but it must be defined otherwise Django will throw an error.

**IMPORTANT**<br>
The value set in `MINIO_STATIC_FILES_BUCKET` must be added either to `MINIO_PRIVATE_BUCKETS` or `MINIO_PUBLIC_BUCKETS`,
otherwise **django-minio-backend** will raise an exception. This setting determines the privacy of generated file URLs which can be unsigned public or signed private.  

**Note:** If `MINIO_STATIC_FILES_BUCKET` is not set, the default value (`auto-generated-bucket-static-files`) will be used. Policy setting for default buckets is **private**.

### Default File Storage Support
**django-minio-backend** can be configured as a default file storage.
To learn more, see [STORAGES](https://docs.djangoproject.com/en/5.1/ref/settings/#std-setting-STORAGES).

To configure **django-minio-backend** as the default file storage, update your `settings.py`:
```python
STORAGES = {  # -- ADDED IN Django 5.1
    "default": {
        "BACKEND": "django_minio_backend.models.MinioBackend",
    }
}
MINIO_MEDIA_FILES_BUCKET = 'my-media-files-bucket'  # replacement for MEDIA_ROOT
# Add the value of MINIO_STATIC_FILES_BUCKET to one of the pre-configured bucket lists. e.g.:
# MINIO_PRIVATE_BUCKETS.append(MINIO_STATIC_FILES_BUCKET)
# MINIO_PUBLIC_BUCKETS.append(MINIO_STATIC_FILES_BUCKET)
```

The value of `MEDIA_URL` is ignored, but it must be defined otherwise Django will throw an error.

**IMPORTANT**<br>
The value set in `MINIO_MEDIA_FILES_BUCKET` must be added either to `MINIO_PRIVATE_BUCKETS` or `MINIO_PUBLIC_BUCKETS`,
otherwise **django-minio-backend** will raise an exception. This setting determines the privacy of generated file URLs which can be unsigned public or signed private.

**Note:** If `MINIO_MEDIA_FILES_BUCKET` is not set, the default value (`auto-generated-bucket-media-files`) will be used. Policy setting for default buckets is **private**.

### URL Caching
**django-minio-backend** includes a caching layer for pre-signed URLs to improve performance. This is particularly useful for applications that frequently access the same files, as it prevents regenerating URLs for the same objects repeatedly.

The cache uses Django's cache framework and stores URLs with a key based on the bucket name, file name, and ETag for uniqueness. For public buckets, caching is skipped as the URLs are static.

URL caching is **disabled by default**. To enable and configure URL caching, you can set the following parameters in your `settings.py`:
```python
# URL caching configuration (optional)
MINIO_URL_CACHING_ENABLED = True  # Enable URL caching (disabled by default)
MINIO_URL_CACHE_TIMEOUT = 60 * 60 * 8  # 8 hours in seconds
MINIO_URL_CACHE_PREFIX = 'minio_url_'  # Prefix for cache keys
```

If `MINIO_URL_CACHE_TIMEOUT` is not set, it defaults to 80% of `MINIO_URL_EXPIRY_HOURS` to ensure cached URLs don't expire before they're regenerated.

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

### Management Commands

#### initialize_buckets
This `django-admin` command creates both the private and public buckets in case one of them does not exist,
and sets the *public* bucket's privacy policy from `private`(default) to `public`.<br>
    ```bash
    python manage.py initialize_buckets
    ```

    Code reference: [initialize_buckets.py](django_minio_backend/management/commands/initialize_buckets.py).

#### clean_orphaned_minio_files
This management command helps maintain the integrity of your MinIO storage by:

1. Identifying and removing orphaned files in MinIO buckets that are no longer referenced in the database
2. Identifying database references to files that no longer exist in MinIO buckets

Usage:
```bash
python manage.py clean_orphaned_minio_files [--dry-run] [--check-missing]
```

Options:
- `--dry-run`: Run without actually deleting files (simulation mode)
- `--check-missing`: Check for database references to missing MinIO files

This command is useful for periodic maintenance to ensure your storage and database remain in sync, preventing storage leaks and identifying broken references.

### Reference Implementation
For a reference implementation, see [Examples](examples).

## Behaviour
The following list summarises the key characteristics of **django-minio-backend**:
  * Bucket existence is **not** checked on a save by default.
    To enable this guard, set `MINIO_BUCKET_CHECK_ON_SAVE = True` in your `settings.py`.
  * Bucket existences are **not** checked on Django start by default.
    To enable this guard, set `MINIO_CONSISTENCY_CHECK_ON_START = True` in your `settings.py`.
  * Many configuration errors are validated through `AppConfig` but not every error can be captured there.
  * Files with the same name in the same bucket are **not** replaced on save by default. Django will store the newer file with an altered file name
    To allow replacing existing files, pass the `replace_existing=True` kwarg to `MinioBackend`.
    For example:
    ```python
    image = models.ImageField(storage=MinioBackend(bucket_name='images-public', replace_existing=True))
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
