# Standard python packages
import json
from datetime import datetime, timedelta
from pathlib import Path
from time import mktime
from typing import Union
import urllib3

# Django packages
from django.conf import settings
from django.core.files.storage import Storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.deconstruct import deconstructible
from django.utils.timezone import utc
# Third-party (MinIO) packages
from minio import Minio
from minio.definitions import Object
from minio.error import NoSuchKey, NoSuchBucket
from urllib3.exceptions import MaxRetryError
# Local Packages
from .utils import MinioServerStatus


__all__ = ['MinioBackend', 'get_iso_date', 'iso_date_prefix']


def get_setting(name, default=None):
    return getattr(settings, name, default)


def get_iso_date() -> str:
    now = datetime.utcnow().replace(tzinfo=utc)
    return f"{now.year}-{now.month}-{now.day}"


def iso_date_prefix(_, file_name_ext: str) -> str:
    return f"{get_iso_date()}/{file_name_ext}"


@deconstructible
class MinioBackend(Storage):
    def __init__(self, *args, **kwargs):
        self._META_ARGS = args
        self._META_KWARGS = kwargs
        self._BUCKET: str = kwargs.get("bucket", "")
        self.MINIO_ENDPOINT: str = get_setting("MINIO_ENDPOINT")
        self.MINIO_ACCESS_KEY: str = get_setting("MINIO_ACCESS_KEY")
        self.MINIO_SECRET_KEY: str = get_setting("MINIO_SECRET_KEY")
        self.MINIO_USE_HTTPS: bool = get_setting("MINIO_USE_HTTPS")
        self.MINIO_PRIVATE_BUCKET_NAME: str = get_setting("MINIO_PRIVATE_BUCKET_NAME", "")
        self.MINIO_PUBLIC_BUCKET_NAME: str = get_setting("MINIO_PUBLIC_BUCKET_NAME", "")
        self.IS_PUBLIC: bool = kwargs.get("is_public", False)
        self.HTTP_CLIENT: urllib3.poolmanager.PoolManager = kwargs.get("http_client", None)  # https://docs.min.io/docs/python-client-api-reference.html
        self._client: Union[Minio, None] = None

    def is_minio_available(self) -> MinioServerStatus:
        if not self.MINIO_ENDPOINT:
            mss = MinioServerStatus(None)
            mss.add_message('MINIO_ENDPOINT is not configured in Django settings')
            return mss

        http = urllib3.PoolManager()
        try:
            r = http.request('GET', f'{self.MINIO_ENDPOINT}/minio/index.html', timeout=10.0)
            return MinioServerStatus(r)
        except urllib3.exceptions.MaxRetryError:
            mss = MinioServerStatus(None)
            mss.add_message(f'Could not open connection to {self.MINIO_ENDPOINT}/minio/index.html ...')
            return mss
        except Exception as e:
            mss = MinioServerStatus(None)
            mss.add_message(repr(e))
            return mss

    # django.core.files.storage.Storage
    def _save(self, file_path_name: str, content: InMemoryUploadedFile):
        """
        Saves file to Minio by implementing Minio.put_object()
        :param file_path_name (str): Path to file + file name + file extension | ie.: images/2018-12-31/cat.png
        :param content (InMemoryUploadedFile): File object
        :return:
        """
        # Check if bucket exists, create if not
        if not self.client.bucket_exists(self._BUCKET):
            self.client.make_bucket(self._BUCKET)

        # Upload object
        file_path = Path(file_path_name)  # app name + file.suffix
        self.client.put_object(
            bucket_name=self._BUCKET,
            object_name=file_path.as_posix(),
            data=content,
            length=content.size,
            content_type=content.content_type,
            metadata=None,
            sse=None,
            progress=None
        )
        return file_path.as_posix()

    def _open(self, bucket_name, object_name, request_headers=None, sse=None):
        return self.client.get_object(bucket_name, object_name, request_headers, sse)

    def stat(self, name: str) -> Union[Object, bool]:
        object_name = Path(name).as_posix()
        try:
            obj = self.client.stat_object(self._BUCKET, object_name=object_name)
            return obj
        except (NoSuchKey, NoSuchBucket):
            return False
        except MaxRetryError:
            return False

    def delete(self, name: str):
        """
        Deletes an object in Django and MinIO.
        This method is called only when an object is deleted from it's own `change view` ie.:
        http://django.test/admin/upload/privateattachment/13/change/
        This method is NOT called during a bulk_delete order!
        :param name: File object name
        """
        object_name = Path(name).as_posix()
        self.client.remove_object(bucket_name=self._BUCKET, object_name=object_name)

    def exists(self, name: str) -> bool:
        object_name = Path(name).as_posix()
        if self.stat(object_name):
            return True
        return False

    def listdir(self, bucket_name: str):
        objects = self.client.list_objects_v2(bucket_name=bucket_name, recursive=True)
        return [(obj.object_name, obj) for obj in objects]

    def size(self, name: str) -> int:
        object_name = Path(name).as_posix()
        obj = self.stat(object_name)
        if obj:
            return obj.size
        return 0

    def url(self, name: str):
        """
        Returns url to object.
        If bucket is public, direct link is provided.
        if bucket is private, a pre-signed link is provided.
        :param name: (str) file path + file name + suffix
        :return: (str) URL to object
        """
        if self.IS_PUBLIC:
            # noinspection PyProtectedMember
            return f'{self.client._endpoint_url}/{self._BUCKET}/{name}'

        try:
            return self.client.presigned_get_object(
                bucket_name=self._BUCKET,
                object_name=name.encode('utf-8'),
                expires=get_setting("MINIO_URL_EXPIRY_HOURS", timedelta(days=7))  # Default is 7 days
            )
        except MaxRetryError:
            raise ConnectionError("Couldn't connect to Minio. Check django_minio_backend parameters in Django-Settings")

    def path(self, name):
        raise NotImplementedError("Storage system can't be accessed using open().")

    def get_accessed_time(self, name: str) -> datetime:
        """
        Return the last accessed time (as a datetime) of the file specified by
        name. The datetime will be timezone-aware if USE_TZ=True.
        """
        return datetime(year=1970, month=1, day=1, hour=0, minute=0, second=0)

    def get_created_time(self, name: str) -> datetime:
        """
        Return the creation time (as a datetime) of the file specified by name.
        The datetime will be timezone-aware if USE_TZ=True.
        """
        return datetime(year=1970, month=1, day=1, hour=0, minute=0, second=0)

    def get_modified_time(self, name: str) -> datetime:
        """
        Return the last modified time (as a datetime) of the file specified by
        name. The datetime will be timezone-aware if USE_TZ=True.
        """
        obj = self.stat(name)
        return datetime.fromtimestamp(mktime(obj.last_modified))

    # MinioBackend
    @property
    def client(self) -> Minio:
        if not self._client:
            self.new_client()
            return self._client
        return self._client

    def new_client(self):
        """
        Instantiates a new Minio client and
        :return:
        """
        # Safety Guards
        if self._BUCKET and self.IS_PUBLIC:
            raise AttributeError("You cannot set both `bucket` and `is_public`!")
        if not self.MINIO_PRIVATE_BUCKET_NAME or not self.MINIO_PUBLIC_BUCKET_NAME:
            raise AttributeError("MINIO_PRIVATE_BUCKET_NAME or MINIO_PUBLIC_BUCKET_NAME is not configured properly.")

        if self._BUCKET:
            pass  # We optimistically trust the bucket name here
        elif self.IS_PUBLIC:
            self._BUCKET = self.MINIO_PUBLIC_BUCKET_NAME
        elif not self.IS_PUBLIC:
            self._BUCKET = self.MINIO_PRIVATE_BUCKET_NAME

        minio_client = Minio(
            endpoint=self.MINIO_ENDPOINT,
            access_key=self.MINIO_ACCESS_KEY,
            secret_key=self.MINIO_SECRET_KEY,
            secure=self.MINIO_USE_HTTPS,
            http_client=self.HTTP_CLIENT,
        )
        self._client = minio_client

    # MAINTENANCE
    def check_bucket_existences(self):  # Execute this handler upon starting Django to make sure buckets exist
        if not self.client.bucket_exists(self.MINIO_PRIVATE_BUCKET_NAME):
            self.client.make_bucket(bucket_name=self.MINIO_PRIVATE_BUCKET_NAME)
        if not self.client.bucket_exists(self.MINIO_PUBLIC_BUCKET_NAME):
            self.client.make_bucket(bucket_name=self.MINIO_PUBLIC_BUCKET_NAME)

    def set_bucket_to_public(self, bucket_name):
        policy_read_only = {"Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Sid": "",
                                    "Effect": "Allow",
                                    "Principal": {"AWS": "*"},
                                    "Action": "s3:GetBucketLocation",
                                    "Resource": f"arn:aws:s3:::{bucket_name}"
                                },
                                {
                                    "Sid": "",
                                    "Effect": "Allow",
                                    "Principal": {"AWS": "*"},
                                    "Action": "s3:ListBucket",
                                    "Resource": f"arn:aws:s3:::{bucket_name}"
                                },
                                {
                                    "Sid": "",
                                    "Effect": "Allow",
                                    "Principal": {"AWS": "*"},
                                    "Action": "s3:GetObject",
                                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                                }
                            ]}
        self.client.set_bucket_policy(bucket_name=bucket_name, policy=json.dumps(policy_read_only))
