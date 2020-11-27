import io
import json
import mimetypes
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from time import mktime
from typing import Union, List

# noinspection PyPackageRequirements minIO_requirement
import certifi
import minio.definitions
import minio.error
# noinspection PyPackageRequirements minIO_requirement
import urllib3
from django.core.files import File
from django.core.files.storage import Storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.deconstruct import deconstructible
from django.utils.timezone import utc
from minio import Minio

from .utils import MinioServerStatus, PrivatePublicMixedError, ConfigurationError, get_setting

__all__ = ['MinioBackend', 'get_iso_date', 'iso_date_prefix', ]


def get_iso_date() -> str:
    now = datetime.utcnow().replace(tzinfo=utc)
    return f"{now.year}-{now.month}-{now.day}"


def iso_date_prefix(_, file_name_ext: str) -> str:
    return f"{get_iso_date()}/{file_name_ext}"


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

    def __init__(self,
                 bucket_name: str,
                 *args,
                 **kwargs):

        self._BUCKET_NAME: str = bucket_name
        self._META_ARGS = args
        self._META_KWARGS = kwargs

        self._REPLACE_EXISTING = kwargs.get('replace_existing', False)

        self.__CLIENT: Union[Minio, None] = None
        self.__MINIO_ENDPOINT: str = get_setting("MINIO_ENDPOINT")
        self.__MINIO_ACCESS_KEY: str = get_setting("MINIO_ACCESS_KEY")
        self.__MINIO_SECRET_KEY: str = get_setting("MINIO_SECRET_KEY")
        self.__MINIO_USE_HTTPS: bool = get_setting("MINIO_USE_HTTPS")

        self.PRIVATE_BUCKETS: List[str] = get_setting("MINIO_PRIVATE_BUCKETS", [])
        self.PUBLIC_BUCKETS: List[str] = get_setting("MINIO_PUBLIC_BUCKETS", [])

        # https://docs.min.io/docs/python-client-api-reference.html
        self.HTTP_CLIENT: urllib3.poolmanager.PoolManager = kwargs.get("http_client", None)

        bucket_name_intersection: List[str] = list(set(self.PRIVATE_BUCKETS) & set(self.PUBLIC_BUCKETS))
        if bucket_name_intersection:
            raise PrivatePublicMixedError(
                f'One or more buckets have been declared both private and public: {bucket_name_intersection}'
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
        # Check if bucket exists, create if not
        self.check_bucket_existence()

        # Check if object with name already exists; delete if so
        if self._REPLACE_EXISTING and self.stat(file_path_name):
            self.delete(file_path_name)

        # Upload object
        file_path: Path = Path(file_path_name)  # app name + file.suffix
        self.client.put_object(
            bucket_name=self._BUCKET_NAME,
            object_name=file_path.as_posix(),
            data=content,
            length=content.size,
            content_type=self._guess_content_type(file_path_name, content),
            metadata=self._META_KWARGS.get('metadata', None),
            sse=self._META_KWARGS.get('sse', None),
            progress=self._META_KWARGS.get('progress', None),
        )
        return file_path.as_posix()

    def _open(self, object_name, mode='rb', **kwargs):
        """
        Implements the Storage._open(name,mode='rb') method
        :param name (str): object_name [path to file excluding bucket name which is implied]
        :kwargs (dict): passed on to the underlying minIO client's get_object() method
        """
        resp: urllib3.response.HTTPResponse = urllib3.response.HTTPResponse()

        if mode != 'rb':
            raise ValueError('Files retrieved from minIO are read-only. Use save() method to override contents')
        try:
            resp = self.client.get_object(self._BUCKET_NAME, object_name, kwargs)
            file = File(file=io.BytesIO(resp.read()), name=object_name)
        finally:
            resp.close()
            resp.release_conn()
        return file

    def stat(self, name: str) -> Union[minio.definitions.Object, bool]:
        object_name = Path(name).as_posix()
        try:
            obj = self.client.stat_object(self._BUCKET_NAME, object_name=object_name)
            return obj
        except (minio.error.NoSuchKey, minio.error.NoSuchBucket):
            return False
        except urllib3.exceptions.MaxRetryError:
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
        self.client.remove_object(bucket_name=self._BUCKET_NAME, object_name=object_name)

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
        if self.is_bucket_public:
            # noinspection PyProtectedMember
            return f'{self.client._endpoint_url}/{self._BUCKET_NAME}/{name}'

        try:
            return self.client.presigned_get_object(
                bucket_name=self._BUCKET_NAME,
                object_name=name.encode('utf-8'),
                expires=get_setting("MINIO_URL_EXPIRY_HOURS", timedelta(days=7))  # Default is 7 days
            )
        except urllib3.exceptions.MaxRetryError:
            raise ConnectionError("Couldn't connect to Minio. Check django_minio_backend parameters in Django-Settings")

    def path(self, name):
        raise NotImplementedError("The minIO storage system doesn't support absolute paths.")

    def get_accessed_time(self, name: str) -> datetime:
        """
        Return the last accessed time (as a datetime) of the file specified by
        name. The datetime will be timezone-aware if USE_TZ=True.
        """
        raise NotImplementedError('minIO does not store last accessed time')

    def get_created_time(self, name: str) -> datetime:
        """
        Return the creation time (as a datetime) of the file specified by name.
        The datetime will be timezone-aware if USE_TZ=True.
        """
        raise NotImplementedError('minIO does not store creation time')

    def get_modified_time(self, name: str) -> datetime:
        """
        Return the last modified time (as a datetime) of the file specified by
        name. The datetime will be timezone-aware if USE_TZ=True.
        """
        obj = self.stat(name)
        return datetime.fromtimestamp(mktime(obj.last_modified))

    @staticmethod
    def _guess_content_type(file_path_name: str, content: InMemoryUploadedFile):
        if hasattr(content, 'content_type'):
            return content.content_type
        guess = mimetypes.guess_type(file_path_name)[0]
        if guess is None:
            return 'application/octet-stream'  # default
        return guess

    """
        MinioBackend
    """

    @property
    def bucket(self) -> str:
        return self._BUCKET_NAME

    @property
    def is_bucket_public(self) -> bool:
        return True if self._BUCKET_NAME in self.PUBLIC_BUCKETS else False

    def is_minio_available(self) -> MinioServerStatus:
        if not self.__MINIO_ENDPOINT:
            mss = MinioServerStatus(None)
            mss.add_message('MINIO_ENDPOINT is not configured in Django settings')
            return mss

        with urllib3.PoolManager(cert_reqs=ssl.CERT_REQUIRED, ca_certs=certifi.where()) as http:
            try:
                scheme = "https" if self.__MINIO_USE_HTTPS else "http"
                r = http.request('GET', f'{scheme}://{self.__MINIO_ENDPOINT}/minio/index.html')
                return MinioServerStatus(r)
            except urllib3.exceptions.MaxRetryError as e:
                mss = MinioServerStatus(None)
                mss.add_message(f'Could not open connection to {self.__MINIO_ENDPOINT}/minio/index.html\n'
                                f'Reason: {e}')
                return mss
            except Exception as e:
                mss = MinioServerStatus(None)
                mss.add_message(repr(e))
                return mss

    @property
    def client(self) -> Minio:
        if not self.__CLIENT:
            self.new_client()
            return self.__CLIENT
        return self.__CLIENT

    def new_client(self):
        """
        Instantiates a new Minio client and
        :return:
        """
        # Safety Guards
        if not self.PRIVATE_BUCKETS or not self.PUBLIC_BUCKETS:
            raise ConfigurationError(
                'MINIO_PRIVATE_BUCKETS or '
                'MINIO_PUBLIC_BUCKETS '
                'is not configured properly in your settings.py (or equivalent)'
            )

        mc = Minio(
            endpoint=self.__MINIO_ENDPOINT,
            access_key=self.__MINIO_ACCESS_KEY,
            secret_key=self.__MINIO_SECRET_KEY,
            secure=self.__MINIO_USE_HTTPS,
            http_client=self.HTTP_CLIENT,
        )
        self.__CLIENT = mc

    # MAINTENANCE
    def check_bucket_existence(self):
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(bucket_name=self.bucket)

    def check_bucket_existences(self):  # Execute this handler upon starting Django to make sure buckets exist
        for bucket in [*self.PUBLIC_BUCKETS, *self.PRIVATE_BUCKETS]:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket_name=bucket)

    def set_bucket_policy(self, bucket: str, policy: dict):
        self.client.set_bucket_policy(bucket_name=bucket, policy=json.dumps(policy))

    def set_bucket_to_public(self):
        policy_public_read_only = {"Version": "2012-10-17",
                                   "Statement": [
                                       {
                                           "Sid": "",
                                           "Effect": "Allow",
                                           "Principal": {"AWS": "*"},
                                           "Action": "s3:GetBucketLocation",
                                           "Resource": f"arn:aws:s3:::{self.bucket}"
                                       },
                                       {
                                           "Sid": "",
                                           "Effect": "Allow",
                                           "Principal": {"AWS": "*"},
                                           "Action": "s3:ListBucket",
                                           "Resource": f"arn:aws:s3:::{self.bucket}"
                                       },
                                       {
                                           "Sid": "",
                                           "Effect": "Allow",
                                           "Principal": {"AWS": "*"},
                                           "Action": "s3:GetObject",
                                           "Resource": f"arn:aws:s3:::{self.bucket}/*"
                                       }
                                   ]}
        self.set_bucket_policy(self.bucket, policy_public_read_only)
