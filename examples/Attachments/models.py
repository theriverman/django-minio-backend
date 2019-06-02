import datetime
from django.db import models, router
from django.utils.timezone import utc
from django.db.models.deletion import Collector
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django_minio_backend import MinioBackend, iso_date_prefix


def get_iso_date() -> str:
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    return f"{now.year}-{now.month}-{now.day}"


# Create your models here.
class PublicAttachment(models.Model):
    def set_file_path_name(self, file_name_ext: str) -> str:
        """
        Defines the full absolute path to the file in the bucket. The original content's type is used as parent folder.
        :param file_name_ext: (str) File name + extension. ie.: cat.png OR images/animals/2019/cat.png
        :return: (str) Absolute path to file in Minio Bucket
        """
        return f"{get_iso_date()}/{self.content_type}/{file_name_ext}"

    def delete(self, using=None, keep_parents=False):
        """
        Delete must be overridden because the inherited delete method does not call `self.file.delete()`.
        """
        using = using or router.db_for_write(self.__class__, instance=self)
        assert self.pk is not None, (
                "%s object can't be deleted because its %s attribute is set to None." %
                (self._meta.object_name, self._meta.pk.attname)
        )

        collector = Collector(using=using)
        collector.collect([self], keep_parents=keep_parents)
        self.file.delete()
        return collector.delete()

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
    content_type: ContentType = models.ForeignKey(ContentType, null=False, blank=False, on_delete=models.CASCADE,
                                                  verbose_name="Content Type")
    object_id = models.PositiveIntegerField(null=False, blank=False, verbose_name="Related Object's ID")
    content_object = GenericForeignKey("content_type", "object_id")

    file = models.FileField(verbose_name="Object Upload", storage=MinioBackend(is_public=True),
                            upload_to=iso_date_prefix)


class PrivateAttachment(models.Model):
    def set_file_path_name(self, file_name_ext: str) -> str:
        """
        Defines the full absolute path to the file in the bucket. The original content's type is used as parent folder.
        :param file_name_ext: (str) File name + extension. ie.: cat.png OR images/animals/2019/cat.png
        :return: (str) Absolute path to file in Minio Bucket
        """
        return f"{get_iso_date()}/{self.content_type}/{file_name_ext}"

    def delete(self, using=None, keep_parents=False):
        using = using or router.db_for_write(self.__class__, instance=self)
        assert self.pk is not None, (
                "%s object can't be deleted because its %s attribute is set to None." %
                (self._meta.object_name, self._meta.pk.attname)
        )

        collector = Collector(using=using)
        collector.collect([self], keep_parents=keep_parents)
        self.file.delete()
        return collector.delete()

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
    content_type: ContentType = models.ForeignKey(ContentType, null=False, blank=False, on_delete=models.CASCADE,
                                                  verbose_name="Content Type")
    object_id = models.PositiveIntegerField(null=False, blank=False, verbose_name="Related Object's ID")
    content_object = GenericForeignKey("content_type", "object_id")

    file = models.FileField(verbose_name="Object Upload", storage=MinioBackend(is_public=False),
                            upload_to=set_file_path_name)
