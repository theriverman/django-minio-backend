"""
django-minio-backend
A MinIO-compatible custom storage backend for Django

References:
  * https://github.com/minio/minio-py
  * https://docs.djangoproject.com/en/3.2/howto/custom-file-storage/
"""
import io
import json
import logging
import mimetypes
import ssl
import datetime
from pathlib import Path
from typing import Union, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Union, List
import hashlib
from datetime import timedelta

# noinspection PyPackageRequirements MinIO_requirement
import certifi
import minio
import minio.datatypes
import minio.error
import minio.helpers
import urllib3
import urllib3.exceptions
from django.core.files import File
from django.core.files.storage import Storage, storages
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.deconstruct import deconstructible
from django.core.cache import cache


from .utils import MinioServerStatus, PrivatePublicMixedError, ConfigurationError, get_setting, get_storages_setting


__all__ = ['MinioBackend', 'MinioBackendStatic', 'get_iso_date', 'iso_date_prefix', ]
logger = logging.getLogger(__name__)


def get_iso_date() -> str:
    """Get current date in ISO8601 format [year-month-day] (zero-padded) as string"""
    now = datetime.datetime.now(datetime.UTC)
    return now.strftime("%Y-%m-%d")


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

    def open(self, mode=None, *args, **kwargs):
        if self.closed:
            self.file = self._storage.open(self.name, mode or "rb").file
        return super().open(mode, *args, **kwargs)


@deconstructible
class MinioBackend(Storage):
    """
    :param bucket_name (str): The bucket's name where file(s) will be stored
    :arg *args: An arbitrary number of arguments. Stored in the self._META_ARGS class field
    :arg **kwargs: An arbitrary number of key-value arguments.
        Stored in the self._META_KWARGS class field
        Through self._META_KWARGS, the "metadata", "sse" and "progress" fields can be set
        for the underlying MinIO SDK's put_object() method
    """
    DEFAULT_MEDIA_FILES_BUCKET = 'auto-generated-bucket-media-files'  # PRIVATE BY DEFAULT

    def __init__(self,
                 bucket_name: str = '',
                 storage_name: str = 'default',
                 *args,
                 **kwargs):
        if not storages.backends[storage_name].get("OPTIONS"):
            raise ConfigurationError("OPTIONS not present in STORAGES in settings.py")
        # received kwargs are preferred. missing keys are filled from storages.backends
        kwargs = {**kwargs, **{k: v for k, v in storages.backends[storage_name]["OPTIONS"].items() if k not in kwargs}}

        # If bucket_name is not provided, MinioBackend falls back to using DEFAULT_MEDIA_FILES_BUCKET
        # See https://docs.djangoproject.com/en/3.2/ref/settings/#default-file-storage
        if not bucket_name or bucket_name == '':
            self._BUCKET_NAME: str = kwargs.get("MINIO_DEFAULT_BUCKET", self.DEFAULT_MEDIA_FILES_BUCKET)
        else:
            self._BUCKET_NAME: str = bucket_name

        self._META_ARGS = args
        self._META_KWARGS = kwargs

        self._REPLACE_EXISTING = kwargs.get('replace_existing', False)

        self.__CLIENT: Union[minio.Minio, None] = None  # This client is used for internal communication only. Communication this way should not leave the host network's perimeter
        self.__CLIENT_EXT: Union[minio.Minio, None] = None  # This client is used for external communication. This client is necessary for creating region-aware pre-signed URLs
        self.__MINIO_ENDPOINT: str = kwargs.get("MINIO_ENDPOINT", "")
        self.__MINIO_EXTERNAL_ENDPOINT: str = kwargs.get("MINIO_EXTERNAL_ENDPOINT", self.__MINIO_ENDPOINT)
        self.__MINIO_ACCESS_KEY: str = kwargs.get("MINIO_ACCESS_KEY")
        self.__MINIO_SECRET_KEY: str = kwargs.get("MINIO_SECRET_KEY")
        self.__MINIO_USE_HTTPS: bool = kwargs.get("MINIO_USE_HTTPS")
        self.__MINIO_REGION: str = kwargs.get("MINIO_REGION", "us-east-1")  # MINIO defaults to "us-east-1" when region is set to None
        self.__MINIO_EXTERNAL_ENDPOINT_USE_HTTPS: bool = kwargs.get("MINIO_EXTERNAL_ENDPOINT_USE_HTTPS", self.__MINIO_USE_HTTPS)
        self.__MINIO_BUCKET_CHECK_ON_SAVE: bool = kwargs.get("MINIO_BUCKET_CHECK_ON_SAVE", False)
        self.__MINIO_URL_EXPIRY_HOURS = kwargs.get("MINIO_URL_EXPIRY_HOURS", datetime.timedelta(days=7))
        self.__BASE_URL = f'{"https://" if self.__MINIO_USE_HTTPS else "http://"}{self.__MINIO_ENDPOINT}'
        self.__BASE_URL_EXTERNAL = f'{"https://" if self.__MINIO_EXTERNAL_ENDPOINT_USE_HTTPS else "http://"}{self.__MINIO_EXTERNAL_ENDPOINT}'
        self.__SAME_ENDPOINTS = self.__MINIO_ENDPOINT == self.__MINIO_EXTERNAL_ENDPOINT

        self.PRIVATE_BUCKETS: List[str] = kwargs.get("MINIO_PRIVATE_BUCKETS", [])
        self.PUBLIC_BUCKETS: List[str] = kwargs.get("MINIO_PUBLIC_BUCKETS", [])
        if self.bucket == self.DEFAULT_MEDIA_FILES_BUCKET:
            self.PRIVATE_BUCKETS.append(self.DEFAULT_MEDIA_FILES_BUCKET)

        if self.bucket not in [*self.PRIVATE_BUCKETS, *self.PUBLIC_BUCKETS]:
            logger.warning(f'Bucket ({self.bucket}) is not declared either in MINIO_PRIVATE_BUCKETS or '
                           f'MINIO_PUBLIC_BUCKETS. Falling back to defaults treating bucket as PRIVATE.')
            self.PRIVATE_BUCKETS.append(self.bucket)

        # https://docs.min.io/docs/python-client-api-reference.html
        http_client_from_kwargs = self._META_KWARGS.get("http_client", None)
        http_client_from_settings = kwargs.get("MINIO_HTTP_CLIENT")
        self.HTTP_CLIENT: urllib3.poolmanager.PoolManager = http_client_from_kwargs or http_client_from_settings

        if bucket_name_intersection := list(set(self.PRIVATE_BUCKETS) & set(self.PUBLIC_BUCKETS)):
            raise PrivatePublicMixedError(
                f'One or more buckets have been declared both private and public: {bucket_name_intersection}'
            )
        # Backend extension that caches presigned URLs to avoid regenerating them
        #     on every request. The cache key is based on the file name and ETag.
        self.url_caching_enabled = get_setting('MINIO_URL_CACHING_ENABLED', False)
        self.url_cache_timeout = get_setting(
            'MINIO_URL_CACHE_TIMEOUT',
            int(get_setting('MINIO_URL_EXPIRY_HOURS', timedelta(days=1)).total_seconds() * 0.8)
        )
        # Cache prefix to avoid collisions
        self.cache_prefix = get_setting('MINIO_URL_CACHE_PREFIX', 'minio_url_')

        # Multipart upload configuration
        self.__MINIO_MULTIPART_UPLOAD: bool = kwargs.get('MINIO_MULTIPART_UPLOAD', False)
        self.__MINIO_MULTIPART_THRESHOLD: int = kwargs.get('MINIO_MULTIPART_THRESHOLD', 10 * 1024 * 1024)  # 10MB default
        self.__MINIO_MULTIPART_PART_SIZE: int = kwargs.get('MINIO_MULTIPART_PART_SIZE', 10 * 1024 * 1024)  # 10MB default

        self.validate_settings()
    """
        django.core.files.storage.Storage
    """

    def _save(self, file_path_name: str, content: InMemoryUploadedFile) -> str:
        """
        Saves a file to Minio by implementing Minio.put_object()
        :param file_path_name (str): Path to file + file name + file extension | i.e.: images/2018-12-31/cat.png
        :param content (InMemoryUploadedFile): File object
        :return:
        """
        if self.__MINIO_BUCKET_CHECK_ON_SAVE:
            # Create a bucket if not exists
            self.check_bucket_existence()

        # Check if an object with a name already exists; delete it if so
        try:
            if self._REPLACE_EXISTING and self.stat(file_path_name):
                self.delete(file_path_name)
        except (minio.error.S3Error, minio.error.ServerError, urllib3.exceptions.MaxRetryError, AttributeError):
            pass

        # Upload object
        file_path: Path = Path(file_path_name)  # app name + file.suffix

        # Determine file size
        content.seek(0, 2)  # Seek to end
        file_size = content.tell()
        content.seek(0)  # Reset to beginning

        # Decide whether to use multipart upload
        use_multipart = self.__MINIO_MULTIPART_UPLOAD and file_size >= self.__MINIO_MULTIPART_THRESHOLD

        if use_multipart:
            # Use multipart upload for large files
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=file_path.as_posix(),
                data=content,
                length=-1,
                part_size=self.__MINIO_MULTIPART_PART_SIZE,
                content_type=self._guess_content_type(file_path_name, content),
                metadata=self._META_KWARGS.get('metadata', None),
                sse=self._META_KWARGS.get('sse', None),
                progress=self._META_KWARGS.get('progress', None),
            )
        else:
            # Traditional upload - read entire file into memory
            content_bytes: io.BytesIO = io.BytesIO(content.read())
            content_length: int = len(content_bytes.getvalue())

            self.client.put_object(
                bucket_name=self.bucket,
                object_name=file_path.as_posix(),
                data=content_bytes,
                length=content_length,
                content_type=self._guess_content_type(file_path_name, content),
                metadata=self._META_KWARGS.get('metadata', None),
                sse=self._META_KWARGS.get('sse', None),
                progress=self._META_KWARGS.get('progress', None),
            )
        return file_path.as_posix()

    def _get_cache_key(self, name: str) -> str:
        """
        Generate a cache key based on the ETag.
        For additional uniqueness, try to include the more unique metadata if available.
        """
        try:
            # Try to get the ETag from the object stats
            obj = self.stat(name)
            etag = obj.etag if hasattr(obj, 'etag') else ''
        except (AttributeError, Exception) as e:
            etag = ''

        # Create a unique key using the bucket name, file name, and ETag
        key_parts = [self.bucket, name, etag]
        key_string = '_'.join(key_parts)

        # Create a hash of the key to ensure it's not too long for the cache
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{self.cache_prefix}{key_hash}"

    def get_available_name(self, name, max_length=None):
        """
        Return a filename that's free on the target storage system and
        available for new content to be written to.
        """
        if self._REPLACE_EXISTING:
            return name
        return super(MinioBackend, self).get_available_name(name, max_length)

    def _open(self, object_name, mode='rb', **kwargs) -> S3File:
        """
        Implements the Storage._open(name,mode='rb') method
        :param name (str): object_name [path to file excluding bucket name which is implied]
        :kwargs (dict): passed on to the underlying MinIO client's get_object() method
        """

        if mode != 'rb':
            raise ValueError('Files retrieved from MinIO are read-only. Use save() method to override contents')
        resp: urllib3.response.HTTPResponse = self.client.get_object(self.bucket, object_name, **kwargs)
        try:
            file = S3File(file=io.BytesIO(resp.read()), name=object_name, storage=self)
            return file
        finally:
            resp.close()
            resp.release_conn()

    def stat(self, name: str) -> minio.datatypes.Object:
        """
        Get object information and metadata of an object
        :raises minio.error.S3Error: If the object doesn't exist
        :raises minio.error.ServerError: If the minio backend couldn't be reached
        :raises urllib3.exceptions.MaxRetryError: If the minio backend request has timed out
        """
        return self.client.stat_object(self.bucket, object_name=Path(name).as_posix())

    def delete(self, name: str):
        """
        Deletes an object in Django and MinIO.
        This method is called only when an object is deleted from its own `change view` i.e.:
        http://django.test/admin/upload/privateattachment/13/change/
        This method is NOT called during a bulk_delete order!
        :param name: File object name
        """
        object_name = Path(name).as_posix()
        self.client.remove_object(bucket_name=self.bucket, object_name=object_name)

    def exists(self, name: str) -> bool:
        """Check if an object with the name already exists"""
        object_name = Path(name).as_posix()
        try:
            self.stat(object_name)
        except (minio.error.S3Error, minio.error.ServerError, urllib3.exceptions.MaxRetryError, AttributeError, FileNotFoundError) as e:
            logger.info(msg=f"Object could not be found: {self.bucket}/{name}", exc_info=e)
            return False
        return True

    def listdir(self, path: str = '', **kwargs) -> Tuple[List[str], List[str]]:
        """
        List the contents of the specified path in the configured bucket.
        Return a 2-tuple of lists: (directories, files).
        This method sets the `recursive` kwarg to True by default.
        The `prefix` key in kwargs will be ignored. Provide it through the `path` arg.
        :kwargs: Passed on to the underlying MinIO client's list_objects() method
        """
        prefix = path.strip('/')
        if prefix:
            prefix += '/'
        else:
            prefix = ''
        prefix_len = len(prefix)

        # Always recursive to find everything under the prefix
        kwargs.setdefault('recursive', True)

        dirs = set()
        files = []

        objects = self.client.list_objects(bucket_name=self.bucket, prefix=prefix, **kwargs)
        for obj in objects:
            relpath = obj.object_name[prefix_len:]
            if not relpath:
                continue
            if '/' in relpath:
                subdir = relpath.split('/', 1)[0]
                dirs.add(subdir)
            else:
                files.append(relpath)
        return sorted(dirs), sorted(files)

    def size(self, name: str) -> int:
        """Get an object's size"""
        try:
            obj = self.stat(Path(name).as_posix())
        except (minio.error.S3Error, minio.error.ServerError, urllib3.exceptions.MaxRetryError, AttributeError, FileNotFoundError):
            return 0
        return obj.size

    def url(self, name: str):
        """
        Returns url to object.
        If the bucket is public, a direct link is provided.
        If the bucket is private, a pre-signed link is provided.
        If bucket is public, direct link is provided.
        if bucket is private, a pre-signed link is provided.
        This method does not use caching by default.
        Set MINIO_URL_CACHING_ENABLED to True in settings.py to enable caching.
        :param name: (str) file path + file name + suffix
        :return: (str) URL to object
        """
        if self.is_bucket_public or not self.url_caching_enabled:
            return self._generate_url(name)

        # For private buckets with caching enabled, check cache first
        cache_key = self._get_cache_key(name)

        if cached_url := cache.get(cache_key):
            return cached_url

        # Cache miss, generate new URL
        if (generated_url := self._generate_url(name)) is None:
            return None

        # Cache the URL
        cache.set(cache_key, generated_url, self.url_cache_timeout)

        return generated_url

    def _generate_url(self, name: str):
        """
        Original URL generation implementation for multiple uses.
        :param name: (str) file path + file name + suffix
        :return: (str) URL to object
        """
        client = self.client if self.same_endpoints else self.client_external

        if self.is_bucket_public:
            # noinspection PyProtectedMember
            base_url = client._base_url.build(method="GET", region=self.__MINIO_REGION).geturl()
            return f'{base_url}{self.bucket}/{name}'

        # private bucket
        try:
            u: str = client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=name,
                expires=self.__MINIO_URL_EXPIRY_HOURS,  # Default is 7 days
            )
            return u
        except urllib3.exceptions.MaxRetryError:
            raise ConnectionError("Couldn't connect to Minio. Check django_minio_backend parameters in Django-Settings")

    def path(self, name):
        """The MinIO storage system doesn't support absolute paths"""
        raise NotImplementedError("The MinIO storage system doesn't support absolute paths.")

    def get_accessed_time(self, name: str) -> datetime.datetime:
        """
        Return the last accessed time (as a datetime) of the file specified by
        name. The datetime will be timezone-aware if USE_TZ=True.
        """
        raise NotImplementedError('MinIO does not store last accessed time')

    def get_created_time(self, name: str) -> datetime.datetime:
        """
        Return the creation time (as a datetime) of the file specified by name.
        The datetime will be timezone-aware if USE_TZ=True.
        """
        raise NotImplementedError('MinIO does not store creation time')

    def get_modified_time(self, name: str) -> datetime.datetime:
        """
        Return the last modified time (as a datetime) of the file specified by
        name. The datetime will be timezone-aware if USE_TZ=True.
        """
        if get_setting("USE_TZ"):
            return self.stat(name).last_modified
        return self.stat(name).last_modified.replace(tzinfo=None)  # remove timezone info

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
            mss.add_message('MINIO_ENDPOINT is not configured in Django settings')
            return mss

        with urllib3.PoolManager(cert_reqs=ssl.CERT_REQUIRED, ca_certs=certifi.where()) as http:
            try:
                r = http.request('GET', f'{self.__BASE_URL}/minio/index.html')
                return MinioServerStatus(r)
            except urllib3.exceptions.MaxRetryError as e:
                mss = MinioServerStatus(None)
                mss.add_message(f'Could not open connection to {self.__BASE_URL}/minio/index.html\n'
                                f'Reason: {e}')
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
        if external:
            if not self.__CLIENT_EXT:
                self.__CLIENT_EXT = minio.Minio(
                    endpoint=self.__MINIO_EXTERNAL_ENDPOINT,
                    access_key=self.__MINIO_ACCESS_KEY,
                    secret_key=self.__MINIO_SECRET_KEY,
                    secure=self.__MINIO_EXTERNAL_ENDPOINT_USE_HTTPS,
                    http_client=self.HTTP_CLIENT,
                    region=self.__MINIO_REGION,
                )
            return self.__CLIENT_EXT
        else:
            if not self.__CLIENT:
                self.__CLIENT = minio.Minio(
                    endpoint=self.__MINIO_ENDPOINT,
                    access_key=self.__MINIO_ACCESS_KEY,
                    secret_key=self.__MINIO_SECRET_KEY,
                    secure=self.__MINIO_USE_HTTPS,
                    http_client=self.HTTP_CLIENT,
                    region=self.__MINIO_REGION,
                )
            return self.__CLIENT

    # MAINTENANCE
    def check_bucket_existence(self):
        """Check if configured bucket [self.bucket] exists"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(bucket_name=self.bucket)

    def check_bucket_existences(self, max_workers: Optional[int] = None):
        """
        Check if all buckets configured in settings.py exist. Create them if they don't.

        Args:
            max_workers: Maximum number of concurrent workers.
                        Defaults to min(bucket_count, 10)

        Raises:
            Exception: If any bucket check or creation fails
        """
        all_buckets = [*self.PUBLIC_BUCKETS, *self.PRIVATE_BUCKETS]

        if not all_buckets:
            logger.warning("No buckets configured")
            return

        # Calculate optimal worker count
        if max_workers is None:
            max_workers = min(len(all_buckets), 10)

        def check_and_create_bucket(bucket: str) -> Tuple[str, bool, Optional[Exception]]:
            """
            Check and create a single bucket.

            Returns:
                Tuple of (bucket_name, already_existed, error)
            """
            try:
                exists = self.client.bucket_exists(bucket)
                if not exists:
                    self.client.make_bucket(bucket_name=bucket)
                    logger.info(f"Created bucket: {bucket}")
                    return bucket, False, None
                else:
                    logger.debug(f"Bucket already exists: {bucket}")
                    return bucket, True, None
            except Exception as exc:
                logger.error(f"Error checking/creating bucket {bucket}: {exc}", exc_info=True)
                return bucket, False, exc

        errors = []
        created_count = 0
        existing_count = 0

        logger.info(f"Checking {len(all_buckets)} buckets with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all bucket checks
            future_to_bucket = {
                executor.submit(check_and_create_bucket, bucket): bucket
                for bucket in all_buckets
            }

            # Process results as they complete
            for future in as_completed(future_to_bucket):
                bucket_name = future_to_bucket[future]
                try:
                    bucket, existed, error = future.result()
                    if error:
                        errors.append((bucket, error))
                    elif existed:
                        existing_count += 1
                    else:
                        created_count += 1
                except Exception as e:
                    # Catch any unexpected errors from the future itself
                    logger.error(f"Unexpected error processing bucket {bucket_name}: {e}")
                    errors.append((bucket_name, e))

        # Summary logging
        logger.info(
            f"Bucket check complete: {existing_count} existed, "
            f"{created_count} created, {len(errors)} errors"
        )

        # Raise if any errors occurred
        if errors:
            error_msg = "\n".join([f"  - {bucket}: {error}" for bucket, error in errors])
            raise Exception(f"Failed to check/create {len(errors)} bucket(s):\n{error_msg}")

    def set_bucket_policy(self, bucket: str, policy: dict):
        """Set a custom bucket policy"""
        self.client.set_bucket_policy(bucket_name=bucket, policy=json.dumps(policy))

    def set_bucket_to_public(self):
        """Set bucket policy to be public. It can be then accessed via public URLs"""
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

    def validate_settings(self):
        """
        validate_settings raises a ConfigurationError exception when one of the following conditions is met:
          * Neither MINIO_PRIVATE_BUCKETS nor MINIO_PUBLIC_BUCKETS have been declared and configured with at least 1 bucket
          * A mandatory parameter (MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY or MINIO_USE_HTTPS) hasn't been declared and configured properly
        """
        # minimum 1 bucket has to be declared
        if not (self.PRIVATE_BUCKETS or self.PUBLIC_BUCKETS):
            raise ConfigurationError(
                'Either '
                'MINIO_PRIVATE_BUCKETS'
                ' or '
                'MINIO_PUBLIC_BUCKETS '
                'must be configured in your settings.py (can be both)'
            )
        # mandatory parameters must be configured
        mandatory_parameters = (self.__MINIO_ENDPOINT, self.__MINIO_ACCESS_KEY, self.__MINIO_SECRET_KEY)
        if not all(mandatory_parameters):
            raise ConfigurationError(
                "A mandatory parameter (MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY or MINIO_USE_HTTPS) hasn't been configured properly"
            )


@deconstructible
class MinioBackendStatic(MinioBackend):
    """
    MinIO-compatible Django custom storage system for Django static files.
    The used bucket can be configured in settings.py through `STORAGES.staticfiles.BACKEND`
    :arg *args: Should not be used for static files. It's here for compatibility only
    :arg **kwargs: Should not be used for static files. It's here for compatibility only
    """
    DEFAULT_STATIC_FILES_BUCKET = 'auto-generated-bucket-static-files'

    def __init__(self, *args, **kwargs):
        static_files_bucket = kwargs.get("MINIO_STATIC_FILES_BUCKET", self.DEFAULT_STATIC_FILES_BUCKET)
        logger.debug(f"MinioBackendStatic.static_files_bucket = {static_files_bucket}")
        kwargs["MINIO_PUBLIC_BUCKETS"] = [static_files_bucket, ]  # hardcoded. static files must be public
        super().__init__(bucket_name=static_files_bucket, storage_name="staticfiles", *args, **kwargs)

    def path(self, name):
        """The MinIO storage system doesn't support absolute paths"""
        raise NotImplementedError("The MinIO storage system doesn't support absolute paths.")

    def get_accessed_time(self, name: str):
        """MinIO does not store last accessed time"""
        raise NotImplementedError('MinIO does not store last accessed time')

    def get_created_time(self, name: str):
        """MinIO does not store creation time"""
        raise NotImplementedError('MinIO does not store creation time')
