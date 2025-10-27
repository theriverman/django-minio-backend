# Migrations

Learn how to migrate your existing Django project utilising **django-minio-backend** from an older version to the latest release.

## Migrating from v3.x to v4.0.0+

[Django 5.1](https://docs.djangoproject.com/en/5.1/releases/5.1/#file-storage) introduced a breaking change:
> The `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE` settings have been removed.

Version 4.0.0 of **django-minio-backend** introduces the following breaking changes to align with this requirement:

### User-Facing Changes
* All MinIO configuration parameters must now be wrapped within the `STORAGES["default"]["OPTIONS"]` dictionary
* Separate control for static files through the `STORAGES["staticfiles"]` configuration
* Support for multiple MinIO endpoints (optional)
* Settings parameter `MINIO_MEDIA_FILES_BUCKET` renamed to `MINIO_DEFAULT_BUCKET`
* Static file buckets are now forced to be public (Django requirement)
* Model field storage declarations must use lazy-loaded callables (see step 4 below)
* `MinioBackend` class now requires a `storage_name` parameter when instantiated directly
* Management command `is_minio_available` updated to work with the new configuration structure
* Improved default setting options for easier configuration

### Internal Changes
* `MinioBackend.listdir()` has been reimplemented to return a 2-tuple of lists meeting the Django Storage API requirements (fixes issue #59)
* Class `DjangoMinioBackendConfig` reworked for better validation
* Added `utils.get_storages_setting()` utility function
* AttributeError is no longer raised; underlying MinIO SDK exceptions are raised instead (see docstrings for details)

### For Contributors
* The project has migrated from `setup.py` to [pyproject.toml](pyproject.toml)
* [uv](https://docs.astral.sh/uv/) is now the default package and project manager
* Unit tests have been updated to run against a local MinIO container instead of play.min.io

---

## How to Migrate

**IMPORTANT**: Read the updated [README.md](README.md) thoroughly before beginning migration to understand the new architecture.

### Step 1: Update the Package
```bash
pip install --upgrade django-minio-backend
```

### Step 2: Update `INSTALLED_APPS`
Change your installed apps configuration to use the full app config path:

**Before:**
```python
INSTALLED_APPS = [
    # ...
    'django_minio_backend',
]
```

**After:**
```python
INSTALLED_APPS = [
    # ...
    'django_minio_backend.apps.DjangoMinioBackendConfig',
]
```

### Step 3: Remove Deprecated Settings
Delete these deprecated settings from your `settings.py`:
* `DEFAULT_FILE_STORAGE`
* `STATICFILES_STORAGE`

### Step 4: Migrate to the New `STORAGES` Configuration

**Before (v3.x):**
```python
DEFAULT_FILE_STORAGE = 'django_minio_backend.models.MinioBackend'

MINIO_ENDPOINT = 'minio.your-company.co.uk'
MINIO_ACCESS_KEY = 'yourMinioAccessKey'
MINIO_SECRET_KEY = 'yourVeryS3cr3tP4ssw0rd'
MINIO_USE_HTTPS = True
MINIO_URL_EXPIRY_HOURS = timedelta(days=1)
MINIO_CONSISTENCY_CHECK_ON_START = True
MINIO_PRIVATE_BUCKETS = ['django-backend-dev-private']
MINIO_PUBLIC_BUCKETS = ['django-backend-dev-public']
MINIO_MEDIA_FILES_BUCKET = 'my-media-files-bucket'  # <-- NOTE: This parameter name changes!
MINIO_BUCKET_CHECK_ON_SAVE = True
```

**After (v4.0.0+):**
```python
from datetime import timedelta

STORAGES = {
    "default": {
        "BACKEND": "django_minio_backend.models.MinioBackend",
        "OPTIONS": {
            "MINIO_ENDPOINT": "minio.your-company.co.uk",
            "MINIO_ACCESS_KEY": "yourMinioAccessKey",
            "MINIO_SECRET_KEY": "yourVeryS3cr3tP4ssw0rd",
            "MINIO_USE_HTTPS": True,
            "MINIO_URL_EXPIRY_HOURS": timedelta(days=1),
            "MINIO_CONSISTENCY_CHECK_ON_START": True,
            "MINIO_PRIVATE_BUCKETS": ['django-backend-dev-private', 'my-media-files-bucket'],
            "MINIO_PUBLIC_BUCKETS": ['django-backend-dev-public'],
            "MINIO_DEFAULT_BUCKET": "my-media-files-bucket",  # <-- RENAMED from MINIO_MEDIA_FILES_BUCKET
            "MINIO_BUCKET_CHECK_ON_SAVE": True,
        },
    },
}
```

**Important notes:**
* All MinIO parameters are now nested within `OPTIONS`
* `MINIO_MEDIA_FILES_BUCKET` has been renamed to `MINIO_DEFAULT_BUCKET`
* Add your default bucket to either `MINIO_PRIVATE_BUCKETS` or `MINIO_PUBLIC_BUCKETS`

### Step 5: Update Model Field Storage Declarations

Model fields must now use lazy-loaded storage callables to avoid Django migration serialisation issues.

**Before (v3.x):**
```python
from django.db import models
from django_minio_backend import MinioBackend, iso_date_prefix

class PrivateAttachment(models.Model):
    file = models.FileField(
        verbose_name="Object Upload",
        storage=MinioBackend(bucket_name='django-backend-dev-private'),
        upload_to=iso_date_prefix
    )
```

**After (v4.0.0+):**

Create a `storages.py` file in your app:
```python
# myapp/storages.py
from django_minio_backend.models import MinioBackend

def get_private_storage():
    return MinioBackend(
        bucket_name='django-backend-dev-private',
        storage_name='default',  # References STORAGES["default"]
    )

def get_public_storage():
    return MinioBackend(
        bucket_name='django-backend-dev-public',
        storage_name='default',
    )
```

Update your models:
```python
# myapp/models.py
from django.db import models
from django_minio_backend import iso_date_prefix
from .storages import get_private_storage

class PrivateAttachment(models.Model):
    file = models.FileField(
        verbose_name="Object Upload",
        storage=get_private_storage,  # Callable, not an instance
        upload_to=iso_date_prefix
    )
```

### Step 6: Update Static Files Configuration (if applicable)

If you were serving static files from MinIO in v3.x, update your configuration:

**Before (v3.x):**
```python
STATICFILES_STORAGE = 'django_minio_backend.models.MinioBackendStatic'
MINIO_STATIC_FILES_BUCKET = 'my-static-files-bucket'
```

**After (v4.0.0+):**
```python
STORAGES = {
    "default": {
        # ... your default storage configuration
    },
    "staticfiles": {
        "BACKEND": "django_minio_backend.models.MinioBackendStatic",
        "OPTIONS": {
            "MINIO_ENDPOINT": "minio.your-company.co.uk",
            "MINIO_ACCESS_KEY": "yourMinioAccessKey",
            "MINIO_SECRET_KEY": "yourVeryS3cr3tP4ssw0rd",
            "MINIO_USE_HTTPS": True,
            "MINIO_STATIC_FILES_BUCKET": "my-static-files-bucket",
            "MINIO_CONSISTENCY_CHECK_ON_START": True,
        },
    },
}
```

**Important**: Static file buckets are forced to be public in v4.0.0+ due to Django requirements.

### Step 7: Create and Apply Migrations

After updating your model storage declarations, generate and apply new migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 8: Verify Configuration

Run the health check to ensure everything is properly configured:

```bash
python manage.py is_minio_available
```

---

## Troubleshooting

### Issue: `AttributeError` when accessing storage
**Solution**: Ensure you're using callable storage functions in model fields, not direct class instances.

### Issue: Static files not loading
**Solution**: Verify that your static files bucket is configured and that `STATIC_URL` is defined (even though its value is ignored).

### Issue: Migration errors related to storage
**Solution**: Ensure all storage declarations use lazy-loaded callables as shown in Step 5.

### Issue: `KeyError` when accessing MinIO settings
**Solution**: Verify all MinIO parameters are nested within the `OPTIONS` dictionary in your `STORAGES` configuration.

---

## Getting Help

If you encounter issues not covered in this guide:
1. Review the updated [README.md](README.md)
2. Check the [DjangoExampleProject](DjangoExampleProject) directory for reference implementations
3. Open an issue on [GitHub](https://github.com/theriverman/django-minio-backend/issues)