from django.db import models
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from minio import Minio
from minio.error import ResponseError


@deconstructible
class MinioBackend(Storage):
    def __init__(self, *args, **kwargs):
        # super(MinioBackend, self).__init__(*args, **kwargs)
        self._MINIO_MEDIA_BUCKET_NAME: str
        self._MINIO_ENDPOINT: str
        self._MINIO_ACCESS_KEY: str
        self._MINIO_SECRET_KEY: str
        self._MINIO_USE_HTTPS: bool
        self.client = None

    def new_client(self):
        self.client = Minio(endpoint=self._MINIO_ENDPOINT,
                            access_key=self._MINIO_ACCESS_KEY,
                            secret_key=self._MINIO_SECRET_KEY,
                            secure=self._MINIO_USE_HTTPS)

    def _open(self):
        pass

    def _save(self):
        self.client.put_object()
        pass

    def delete(self, name):
        return self.client.remove_object(bucket_name=self._MINIO_MEDIA_BUCKET_NAME, object_name=name)

    def exists(self, name):
        pass

    def listdir(self, path):
        pass

    def size(self, name):
        pass

    def url(self, name):
        pass

    def get_valid_name(self, name):
        pass

    def get_available_name(self, name, max_length=None):
        pass
