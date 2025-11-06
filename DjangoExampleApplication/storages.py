"""
It is recommended to initialise your custom MinioBackend instance(s) in a separate file
and import it to your models.py to make the model declaration's storage property value lazy-loaded.
With this maneuver, we can avoid Django hard-coding the bucket_name and storage_name values into generated migrations.
"""

from django_minio_backend.models import MinioBackend
from django.core.files.storage import FileSystemStorage
from django.conf import settings

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

def get_image_storage():
    return MinioBackend(
        bucket_name='django-backend-images-private',
        storage_name='default',
    )

def get_filesystem_storage():
    storages_filesystem = settings.STORAGES.get("filesystem", dict())
    options = storages_filesystem.get("OPTIONS", dict())
    return FileSystemStorage(**options)
