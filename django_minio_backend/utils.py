import urllib3
from typing import Union, List


__all__ = ['MinioServerStatus', ]


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
        self.eval()

    def eval(self):
        if not self._request:
            self._details.append('There was no request provided for MinioServerStatus upon initialisation.')
            return False
        self.status = self._request.status
        self.data = self._request.data.decode() if self._request.data else 'No data available'
        if self.status == 403:  # The request was a legal request, but the server is refusing to respond to it, therefore, it's running
            self._bool = True
        else:
            self._details.append('MinIO is not available.')
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
            return 'Minio Server Available'
        return 'Minio Server Not Available'
