django-minio-backend
----
The `django-minio-backend` provides a wrapper around the 
[MinIO Python Library](https://docs.min.io/docs/python-client-quickstart-guide.html).

# Integration
1) Get the package:<br>
    `python setup.py install`
2) Add `django_minio_backend` to `INSTALLED_APPS`:<br>
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_minio_backend',  # django-minio-backend
]
```
3. Implement your own Attachment handler and integrate django-mino-backend:
```python
import datetime
from django.db import models
from django.utils.timezone import utc
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django_minio_backend.models import MinioBackend


def get_iso_date() -> str:
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    return f"{now.year}-{now.month}-{now.day}"


# noinspection PyUnresolvedReferences
class PrivateAttachment(models.Model):
    def set_file_path_name(self, file_name_ext: str) -> str:
        """
        Defines the full absolute path to the file in the bucket. The original content's type is used as parent folder.
        :param file_name_ext: (str) File name + extension. ie.: cat.png OR images/animals/2019/cat.png
        :return: (str) Absolute path to file in Minio Bucket
        """
        return f"{get_iso_date()}/{self.content_type}/{file_name_ext}"

    id = models.AutoField(primary_key=True, verbose_name="Public Attachment ID")
    content_type: ContentType = models.ForeignKey(ContentType, null=False, blank=False, on_delete=models.CASCADE,
                                                  verbose_name="Content Type")
    object_id = models.PositiveIntegerField(null=False, blank=False, verbose_name="Related Object's ID")
    content_object = GenericForeignKey("content_type", "object_id")
    file = models.FileField(verbose_name="Object Upload", storage=MinioBackend(is_public=False),
                            upload_to=set_file_path_name)
```

# Compatibility
  * Django 2.0 or later <br>
  * Python 3.5.0 or later <br>
**Note:** This library relies heavily on [PEP 484 -- Type Hints](https://www.python.org/dev/peps/pep-0484/) 
which was introduced in *Python 3.5.0*.
