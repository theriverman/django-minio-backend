# noinspection PyPackageRequirements minIO_requirement
import urllib3
from typing import Union, List
from django.conf import settings


__all__ = ['MinioServerStatus', 'PrivatePublicMixedError', 'ConfigurationError', 'get_setting', ]


class MinioServerStatus:
    """
    MinioServerStatus is a simple status info wrapper for checking the availability of a remote MinIO server.
    MinioBackend.is_minio_available() returns a MinioServerStatus instance

    MinioServerStatus can be evaluated with the bool() method:
        ```
        minio_available = MinioBackend.is_minio_available()
        if bool(minio_available):  # bool() can be omitted
            print("OK")
        ```
    """
    def __init__(self, request: Union[urllib3.response.HTTPResponse, None]):
        self._request = request
        self._bool = False
        self._details: List[str] = []
        self.status = None
        self.data = None

        self.__OK = 'MinIO is available'
        self.___NOK = 'MinIO is NOT available'

        if not self._request:
            self.add_message('There was no HTTP request provided for MinioServerStatus upon initialisation.')
        else:
            self.status = self._request.status
            self.data = self._request.data.decode() if self._request.data else 'No data available'
            if self.status == 403:  # Request was a legal, but the server refuses to respond to it -> it's running fine
                self._bool = True
            else:
                self._details.append(self.__OK)
                self._details.append('Reason: ' + self.data)

    def __bool__(self):
        return self._bool

    def add_message(self, text: str):
        self._details.append(text)

    @property
    def is_available(self):
        return self._bool

    @property
    def details(self):
        return '\n'.join(self._details)

    def __repr__(self):
        if self.is_available:
            return self.__OK
        return self.___NOK


class PrivatePublicMixedError(Exception):
    """Raised on public|private bucket configuration collisions"""
    pass


class ConfigurationError(Exception):
    """Raised on django-minio-backend configuration errors"""
    pass


def get_setting(name, default=None):
    """Get setting from settings.py. Return a default value if not defined"""
    return getattr(settings, name, default)
