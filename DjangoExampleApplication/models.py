import uuid
import datetime
from django.db import models
from django.db.models.fields.files import FieldFile
from django.utils.timezone import utc
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django_minio_backend import MinioBackend, iso_date_prefix


def get_iso_date() -> str:
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    return f"{now.year}-{now.month}-{now.day}"


class Image(models.Model):
    """
    This is just for uploaded image
    """
    objects = models.Manager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to=iso_date_prefix, storage=MinioBackend(bucket_name='django-backend-dev-public'))

    def delete(self, *args, **kwargs):
        """
        Delete must be overridden because the inherited delete method does not call `self.image.delete()`.
        """
        # noinspection PyUnresolvedReferences
        self.image.delete()
        super(Image, self).delete(*args, **kwargs)


class GenericAttachment(models.Model):
    """
    This is for demonstrating uploads to the default file storage
    """
    objects = models.Manager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(verbose_name="Object Upload (to default storage)")

    def delete(self, *args, **kwargs):
        """
        Delete must be overridden because the inherited delete method does not call `self.image.delete()`.
        """
        # noinspection PyUnresolvedReferences
        self.file.delete()
        super(GenericAttachment, self).delete(*args, **kwargs)


# Create your models here.
class PublicAttachment(models.Model):
    def set_file_path_name(self, file_name_ext: str) -> str:
        """
        Defines the full absolute path to the file in the bucket. The original content's type is used as parent folder.
        :param file_name_ext: (str) File name + extension. ie.: cat.png OR images/animals/2019/cat.png
        :return: (str) Absolute path to file in Minio Bucket
        """
        return f"{get_iso_date()}/{self.content_type.name}/{file_name_ext}"

    def delete(self, *args, **kwargs):
        """
        Delete must be overridden because the inherited delete method does not call `self.file.delete()`.
        """
        self.file.delete()
        super(PublicAttachment, self).delete(*args, **kwargs)

    @property
    def file_name(self):
        try:
            return self.file.name.split("/")[-1]
        except AttributeError:
            return "[Deleted Object]"

    @property
    def file_size(self):
        return self.file.size

    def __str__(self):
        return str(self.file)

    id = models.AutoField(primary_key=True, verbose_name="Public Attachment ID")
    content_type: ContentType = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE,
                                                  verbose_name="Content Type")
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="Related Object's ID")
    content_object = GenericForeignKey("content_type", "object_id")

    file: FieldFile = models.FileField(verbose_name="Object Upload",
                                       storage=MinioBackend(  # Configure MinioBackend as storage backend here
                                           bucket_name='django-backend-dev-public',
                                       ),
                                       upload_to=iso_date_prefix)


class PrivateAttachment(models.Model):
    def set_file_path_name(self, file_name_ext: str) -> str:
        """
        Defines the full absolute path to the file in the bucket. The original content's type is used as parent folder.
        :param file_name_ext: (str) File name + extension. ie.: cat.png OR images/animals/2019/cat.png
        :return: (str) Absolute path to file in Minio Bucket
        """
        return f"{get_iso_date()}/{self.content_type.name}/{file_name_ext}"

    def delete(self, *args, **kwargs):
        """
        Delete must be overridden because the inherited delete method does not call `self.file.delete()`.
        """
        self.file.delete()
        super(PrivateAttachment, self).delete(*args, **kwargs)

    @property
    def file_name(self):
        try:
            return self.file.name.split("/")[-1]
        except AttributeError:
            return "[Deleted Object]"

    @property
    def file_size(self):
        return self.file.size

    def __str__(self):
        return str(self.file)

    id = models.AutoField(primary_key=True, verbose_name="Public Attachment ID")
    content_type: ContentType = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE,
                                                  verbose_name="Content Type")
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="Related Object's ID")
    content_object = GenericForeignKey("content_type", "object_id")

    file: FieldFile = models.FileField(verbose_name="Object Upload",
                                       storage=MinioBackend(  # Configure MinioBackend as storage backend here
                                           bucket_name='django-backend-dev-private',
                                       ),
                                       upload_to=set_file_path_name)
