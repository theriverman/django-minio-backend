"""
django-minio-backend-five
A MinIO-compatible custom storage backend for Django 5, based on django-minio-backend

References:
  * https://github.com/minio/minio-py
  * https://docs.djangoproject.com/en/4.2/howto/custom-file-storage/
"""

import io
import json
import logging
import mimetypes
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Union

# noinspection PyPackageRequirements MinIO_requirement
import certifi
import minio
import minio.datatypes
import minio.error
import minio.helpers

# noinspection PyPackageRequirements MinIO_requirement
import urllib3
from django.core.files import File
from django.core.files.storage import Storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.deconstruct import deconstructible

from .utils import (
    ConfigurationError,
    MinioServerStatus,
    PrivatePublicMixedError,
    get_setting,
)

__all__ = [
    "MinioBackend",
    "MinioBackendStatic",
    "get_iso_date",
    "iso_date_prefix",
]
logger = logging.getLogger(__name__)


def get_iso_date() -> str:
    """Get current date in ISO8601 format [year-month-day] as string"""
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    return f"{now.year}-{now.month}-{now.day}"


def iso_date_prefix(_, file_name_ext: str) -> str:
    """
    Get filename prepended with current date in ISO8601 format [year-month-day] as string
    The date prefix will be the folder's name storing the object e.g.: 2020-12-31/cat.png
    """
    return f"{get_iso_date()}/{file_name_ext}"


class S3File(File):
    """A file returned from the Minio server"""

    def __init__(self, file, name, storage):
        super().__init__(file, name)
        self._storage = storage

    def open(self, mode=None):
        if self.closed:
            self.file = self._storage.open(self.name, mode or "rb").file
        return super().open(mode)


@deconstructible
class MinioBackend(Storage):
    """
    :param bucket_name (str): The bucket's name where file(s) will be stored
    :arg *args: An arbitrary number of arguments. Stored in the self._META_ARGS class field
    :arg **kwargs: An arbitrary number of key-value arguments.
        Stored in the self._META_KWARGS class field
        Through self._META_KWARGS, the "metadata", "sse" and "progress" fields can be set
        for the underlying put_object() MinIO SDK method
    """

    DEFAULT_MEDIA_FILES_BUCKET = "auto-generated-bucket-media-files"
    DEFAULT_STATIC_FILES_BUCKET = "auto-generated-bucket-static-files"
    DEFAULT_PRIVATE_BUCKETS = [DEFAULT_MEDIA_FILES_BUCKET, DEFAULT_STATIC_FILES_BUCKET]
    MINIO_MEDIA_FILES_BUCKET = get_setting(
        "MINIO_MEDIA_FILES_BUCKET", default=DEFAULT_MEDIA_FILES_BUCKET
    )
    MINIO_STATIC_FILES_BUCKET = get_setting(
        "MINIO_STATIC_FILES_BUCKET", default=DEFAULT_STATIC_FILES_BUCKET
    )

    def __init__(self, bucket_name: str = "", *args, **kwargs):

        # If bucket_name is not provided, MinioBackend acts as a DEFAULT_FILE_STORAGE
        # The automatically selected bucket is MINIO_MEDIA_FILES_BUCKET from settings.py
        # See https://docs.djangoproject.com/en/3.2/ref/settings/#default-file-storage
        if not bucket_name or bucket_name == "":
            self.__CONFIGURED_AS_DEFAULT_STORAGE = True
            self._BUCKET_NAME: str = self.MINIO_MEDIA_FILES_BUCKET
        else:
            self.__CONFIGURED_AS_DEFAULT_STORAGE = False
            self._BUCKET_NAME: str = bucket_name

        self._META_ARGS = args
        self._META_KWARGS = kwargs

        self._REPLACE_EXISTING = kwargs.get("replace_existing", False)

        self.__CLIENT: Union[minio.Minio, None] = (
            None  # This client is used for internal communication only. Communication this way should not leave the host network's perimeter
        )
        self.__CLIENT_EXT: Union[minio.Minio, None] = (
            None  # This client is used for external communication. This client is necessary for creating region-aware pre-signed URLs
        )
        self.__MINIO_ENDPOINT: str = get_setting("MINIO_ENDPOINT", "")
        self.__MINIO_EXTERNAL_ENDPOINT: str = get_setting(
            "MINIO_EXTERNAL_ENDPOINT", self.__MINIO_ENDPOINT
        )
        self.__MINIO_ACCESS_KEY: str = get_setting("MINIO_ACCESS_KEY")
        self.__MINIO_SECRET_KEY: str = get_setting("MINIO_SECRET_KEY")
        self.__MINIO_USE_HTTPS: bool = get_setting("MINIO_USE_HTTPS")
        self.__MINIO_REGION: str = get_setting(
            "MINIO_REGION", "us-east-1"
        )  # MINIO defaults to "us-east-1" when region is set to None
        self.__MINIO_EXTERNAL_ENDPOINT_USE_HTTPS: bool = get_setting(
            "MINIO_EXTERNAL_ENDPOINT_USE_HTTPS", self.__MINIO_USE_HTTPS
        )
        self.__MINIO_BUCKET_CHECK_ON_SAVE: bool = get_setting(
            "MINIO_BUCKET_CHECK_ON_SAVE", False
        )

        self.__BASE_URL = (
            "https://" if self.__MINIO_USE_HTTPS else "http://"
        ) + self.__MINIO_ENDPOINT
        self.__BASE_URL_EXTERNAL = (
            "https://" if self.__MINIO_EXTERNAL_ENDPOINT_USE_HTTPS else "http://"
        ) + self.__MINIO_EXTERNAL_ENDPOINT
        self.__SAME_ENDPOINTS = self.__MINIO_ENDPOINT == self.__MINIO_EXTERNAL_ENDPOINT

        self.PRIVATE_BUCKETS: List[str] = get_setting("MINIO_PRIVATE_BUCKETS", [])
        self.PUBLIC_BUCKETS: List[str] = get_setting("MINIO_PUBLIC_BUCKETS", [])

        # Configure storage type
        self.__STORAGE_TYPE = "custom"
        if self.bucket == self.MINIO_MEDIA_FILES_BUCKET:
            self.__STORAGE_TYPE = "media"
        if self.bucket == self.MINIO_STATIC_FILES_BUCKET:
            self.__STORAGE_TYPE = "static"

        # Enforce good bucket security (private vs public)
        if (self.bucket in self.DEFAULT_PRIVATE_BUCKETS) and (
            self.bucket not in [*self.PRIVATE_BUCKETS, *self.PUBLIC_BUCKETS]
        ):
            self.PRIVATE_BUCKETS.extend(
                self.DEFAULT_PRIVATE_BUCKETS
            )  # policy for default buckets is PRIVATE
        # Require custom buckets to be declared explicitly
        if self.bucket not in [*self.PRIVATE_BUCKETS, *self.PUBLIC_BUCKETS]:
            raise ConfigurationError(
                f"The configured bucket ({self.bucket}) must be declared either in MINIO_PRIVATE_BUCKETS or MINIO_PUBLIC_BUCKETS"
            )

        # https://docs.min.io/docs/python-client-api-reference.html
        http_client_from_kwargs = self._META_KWARGS.get("http_client", None)
        http_client_from_settings = get_setting("MINIO_HTTP_CLIENT")
        self.HTTP_CLIENT: urllib3.poolmanager.PoolManager = (
            http_client_from_kwargs or http_client_from_settings
        )

        bucket_name_intersection: List[str] = list(
            set(self.PRIVATE_BUCKETS) & set(self.PUBLIC_BUCKETS)
        )
        if bucket_name_intersection:
            raise PrivatePublicMixedError(
                f"One or more buckets have been declared both private and public: {bucket_name_intersection}"
            )

    """
        django.core.files.storage.Storage
    """

    def _save(self, file_path_name: str, content: InMemoryUploadedFile) -> str:
        """
        Saves file to Minio by implementing Minio.put_object()
        :param file_path_name (str): Path to file + file name + file extension | ie.: images/2018-12-31/cat.png
        :param content (InMemoryUploadedFile): File object
        :return:
        """
        if self.__MINIO_BUCKET_CHECK_ON_SAVE:
            # Create bucket if not exists
            self.check_bucket_existence()

        # Check if object with name already exists; delete if so
        try:
            if self._REPLACE_EXISTING and self.stat(file_path_name):
                self.delete(file_path_name)
        except AttributeError:
            pass

        # Upload object
        file_path: Path = Path(file_path_name)  # app name + file.suffix
        content_bytes: io.BytesIO = io.BytesIO(content.read())
        content_length: int = len(content_bytes.getvalue())

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=file_path.as_posix(),
            data=content_bytes,
            length=content_length,
            content_type=self._guess_content_type(file_path_name, content),
            metadata=self._META_KWARGS.get("metadata", None),
            sse=self._META_KWARGS.get("sse", None),
            progress=self._META_KWARGS.get("progress", None),
        )
        return file_path.as_posix()

    def get_available_name(self, name, max_length=None):
        """
        Return a filename that's free on the target storage system and
        available for new content to be written to.
        """
        if self._REPLACE_EXISTING:
            return name
        return super(MinioBackend, self).get_available_name(name, max_length)

    def _open(self, object_name, mode="rb", **kwargs) -> S3File:
        """
        Implements the Storage._open(name,mode='rb') method
        :param name (str): object_name [path to file excluding bucket name which is implied]
        :kwargs (dict): passed on to the underlying MinIO client's get_object() method
        """
        resp: urllib3.response.HTTPResponse = urllib3.response.HTTPResponse()

        if mode != "rb":
            raise ValueError(
                "Files retrieved from MinIO are read-only. Use save() method to override contents"
            )
        try:
            resp = self.client.get_object(self.bucket, object_name, kwargs)
            file = S3File(file=io.BytesIO(resp.read()), name=object_name, storage=self)
        finally:
            resp.close()
            resp.release_conn()
        return file

    def stat(self, name: str) -> Union[minio.datatypes.Object, bool]:
        """Get object information and metadata of an object"""
        object_name = Path(name).as_posix()
        try:
            obj = self.client.stat_object(self.bucket, object_name=object_name)
            return obj
        except (
            minio.error.S3Error,
            minio.error.ServerError,
            urllib3.exceptions.MaxRetryError,
        ):
            raise AttributeError(
                f"Could not stat object ({name}) in bucket ({self.bucket})"
            )

    def delete(self, name: str):
        """
        Deletes an object in Django and MinIO.
        This method is called only when an object is deleted from its own `change view` ie.:
        http://django.test/admin/upload/privateattachment/13/change/
        This method is NOT called during a bulk_delete order!
        :param name: File object name
        """
        object_name = Path(name).as_posix()
        self.client.remove_object(bucket_name=self.bucket, object_name=object_name)

    def exists(self, name: str) -> bool:
        """Check if an object with name already exists"""
        object_name = Path(name).as_posix()
        try:
            if self.stat(object_name):
                return True
            return False
        except AttributeError as e:
            logger.info(e)
            return False

    def listdir(self, bucket_name: str):
        """List all objects in a bucket"""
        objects = self.client.list_objects(bucket_name=bucket_name, recursive=True)
        return [(obj.object_name, obj) for obj in objects]

    def size(self, name: str) -> int:
        """Get an object's size"""
        object_name = Path(name).as_posix()
        try:
            obj = self.stat(object_name)
            return obj.size if obj else 0
        except AttributeError:
            return 0

    def url(self, name: str):
        """
        Returns url to object.
        If bucket is public, direct link is provided.
        if bucket is private, a pre-signed link is provided.
        :param name: (str) file path + file name + suffix
        :return: (str) URL to object
        """
        client = self.client if self.same_endpoints else self.client_external

        if self.is_bucket_public:
            # noinspection PyProtectedMember
            base_url = client._base_url.build("GET", self.__MINIO_REGION).geturl()
            return f"{base_url}{self.bucket}/{name}"

        # private bucket
        try:
            u: str = client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=name.encode("utf-8"),
                expires=get_setting(
                    "MINIO_URL_EXPIRY_HOURS", timedelta(days=7)
                ),  # Default is 7 days
            )
            return u
        except urllib3.exceptions.MaxRetryError:
            raise ConnectionError(
                "Couldn't connect to Minio. Check django_minio_backend parameters in Django-Settings"
            )

    def path(self, name):
        """The MinIO storage system doesn't support absolute paths"""
        raise NotImplementedError(
            "The MinIO storage system doesn't support absolute paths."
        )

    def get_accessed_time(self, name: str) -> datetime:
        """
        Return the last accessed time (as a datetime) of the file specified by
        name. The datetime will be timezone-aware if USE_TZ=True.
        """
        raise NotImplementedError("MinIO does not store last accessed time")

    def get_created_time(self, name: str) -> datetime:
        """
        Return the creation time (as a datetime) of the file specified by name.
        The datetime will be timezone-aware if USE_TZ=True.
        """
        raise NotImplementedError("MinIO does not store creation time")

    def get_modified_time(self, name: str) -> datetime:
        """
        Return the last modified time (as a datetime) of the file specified by
        name. The datetime will be timezone-aware if USE_TZ=True.
        """
        if get_setting("USE_TZ"):
            return self.stat(name).last_modified
        return self.stat(name).last_modified.replace(
            tzinfo=None
        )  # remove timezone info

    @staticmethod
    def _guess_content_type(file_path_name: str, content: InMemoryUploadedFile):
        if hasattr(content, "content_type"):
            return content.content_type
        guess = mimetypes.guess_type(file_path_name)[0]
        if guess is None:
            return "application/octet-stream"  # default
        return guess

    """
        MinioBackend
    """

    @property
    def same_endpoints(self) -> bool:
        """
        Returns True if (self.__MINIO_ENDPOINT == self.__MINIO_EXTERNAL_ENDPOINT)
        """
        return self.__SAME_ENDPOINTS

    @property
    def bucket(self) -> str:
        """Get the configured bucket's [self.bucket] name"""
        return self._BUCKET_NAME

    @property
    def is_bucket_public(self) -> bool:
        """Check if configured bucket [self.bucket] is public"""
        return True if self.bucket in self.PUBLIC_BUCKETS else False

    def is_minio_available(self) -> MinioServerStatus:
        """Check if configured MinIO server is available"""
        if not self.__MINIO_ENDPOINT:
            mss = MinioServerStatus(None)
            mss.add_message("MINIO_ENDPOINT is not configured in Django settings")
            return mss

        with urllib3.PoolManager(
            cert_reqs=ssl.CERT_REQUIRED, ca_certs=certifi.where()
        ) as http:
            try:
                r = http.request("GET", f"{self.__BASE_URL}/minio/index.html")
                return MinioServerStatus(r)
            except urllib3.exceptions.MaxRetryError as e:
                mss = MinioServerStatus(None)
                mss.add_message(
                    f"Could not open connection to {self.__BASE_URL}/minio/index.html\n"
                    f"Reason: {e}"
                )
                return mss
            except Exception as e:
                mss = MinioServerStatus(None)
                mss.add_message(repr(e))
                return mss

    @property
    def client(self) -> minio.Minio:
        """
        Get handle to an (already) instantiated minio.Minio instance. This is the default Client.
        If "MINIO_EXTERNAL_ENDPOINT" != MINIO_ENDPOINT, this client is used for internal communication only
        """
        return self.__CLIENT or self._create_new_client()

    @property
    def client_external(self) -> minio.Minio:
        """Get handle to an (already) instantiated EXTERNAL minio.Minio instance for generating pre-signed URLs for external access"""
        return self.__CLIENT_EXT or self._create_new_client(external=True)

    @property
    def base_url(self) -> str:
        """Get internal base URL to MinIO"""
        return self.__BASE_URL

    @property
    def base_url_external(self) -> str:
        """Get external base URL to MinIO"""
        return self.__BASE_URL_EXTERNAL

    def _create_new_client(self, external: bool = False) -> minio.Minio:
        """
        Instantiates a new Minio client and assigns it to their respective class variable
        :param external: If True, the returned value is self.__CLIENT_EXT instead of self.__CLIENT
        """
        self.__CLIENT = minio.Minio(
            endpoint=self.__MINIO_ENDPOINT,
            access_key=self.__MINIO_ACCESS_KEY,
            secret_key=self.__MINIO_SECRET_KEY,
            secure=self.__MINIO_USE_HTTPS,
            http_client=self.HTTP_CLIENT,
            region=self.__MINIO_REGION,
        )
        self.__CLIENT_EXT = minio.Minio(
            endpoint=self.__MINIO_EXTERNAL_ENDPOINT,
            access_key=self.__MINIO_ACCESS_KEY,
            secret_key=self.__MINIO_SECRET_KEY,
            secure=self.__MINIO_EXTERNAL_ENDPOINT_USE_HTTPS,
            http_client=self.HTTP_CLIENT,
            region=self.__MINIO_REGION,
        )
        return self.__CLIENT_EXT if external else self.__CLIENT

    # MAINTENANCE
    def check_bucket_existence(self):
        """Check if configured bucket [self.bucket] exists"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(bucket_name=self.bucket)

    def check_bucket_existences(
        self,
    ):  # Execute this handler upon starting Django to make sure buckets exist
        """Check if all buckets configured in settings.py do exist. If not, create them"""
        for bucket in [*self.PUBLIC_BUCKETS, *self.PRIVATE_BUCKETS]:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket_name=bucket)

    def set_bucket_policy(self, bucket: str, policy: dict):
        """Set a custom bucket policy"""
        self.client.set_bucket_policy(bucket_name=bucket, policy=json.dumps(policy))

    def set_bucket_to_public(self):
        """Set bucket policy to be public. It can be then accessed via public URLs"""
        policy_public_read_only = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetBucketLocation",
                    "Resource": f"arn:aws:s3:::{self.bucket}",
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:ListBucket",
                    "Resource": f"arn:aws:s3:::{self.bucket}",
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket}/*",
                },
            ],
        }
        self.set_bucket_policy(self.bucket, policy_public_read_only)

    def validate_settings(self):
        """
        validate_settings raises a ConfigurationError exception when one of the following conditions is met:
          * Neither MINIO_PRIVATE_BUCKETS nor MINIO_PUBLIC_BUCKETS have been declared and configured with at least 1 bucket
          * A mandatory parameter (MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY or MINIO_USE_HTTPS) hasn't been declared and configured properly
        """
        # minimum 1 bucket has to be declared
        if not (
            get_setting("MINIO_PRIVATE_BUCKETS") or get_setting("MINIO_PUBLIC_BUCKETS")
        ):
            raise ConfigurationError(
                "Either "
                "MINIO_PRIVATE_BUCKETS"
                " or "
                "MINIO_PUBLIC_BUCKETS "
                "must be configured in your settings.py (can be both)"
            )
        # mandatory parameters must be configured
        mandatory_parameters = (
            self.__MINIO_ENDPOINT,
            self.__MINIO_ACCESS_KEY,
            self.__MINIO_SECRET_KEY,
        )
        if any([bool(x) is False for x in mandatory_parameters]) or (
            get_setting("MINIO_USE_HTTPS") is None
        ):
            raise ConfigurationError(
                "A mandatory parameter (MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY or MINIO_USE_HTTPS) hasn't been configured properly"
            )


@deconstructible
class MinioBackendStatic(MinioBackend):
    """
    MinIO-compatible Django custom storage system for Django static files.
    The used bucket can be configured in settings.py through `MINIO_STATIC_FILES_BUCKET`
    :arg *args: Should not be used for static files. It's here for compatibility only
    :arg **kwargs: Should not be used for static files. It's here for compatibility only
    """

    def __init__(self, *args, **kwargs):
        super().__init__(self.MINIO_STATIC_FILES_BUCKET, *args, **kwargs)
        self.check_bucket_existence()  # make sure the `MINIO_STATIC_FILES_BUCKET` exists
        self.set_bucket_to_public()  # the static files bucket must be publicly available

    def path(self, name):
        """The MinIO storage system doesn't support absolute paths"""
        raise NotImplementedError(
            "The MinIO storage system doesn't support absolute paths."
        )

    def get_accessed_time(self, name: str):
        """MinIO does not store last accessed time"""
        raise NotImplementedError("MinIO does not store last accessed time")

    def get_created_time(self, name: str):
        """MinIO does not store creation time"""
        raise NotImplementedError("MinIO does not store creation time")
