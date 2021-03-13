import time
from pathlib import Path
from django.conf import settings
from django.core.files import File
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.core.validators import URLValidator

from DjangoExampleApplication.models import Image, PublicAttachment, PrivateAttachment


test_file_path = Path(settings.BASE_DIR) / "DjangoExampleApplication" / "assets" / "audience-868074_1920.jpg"
test_file_size = 339085


class ImageTestCase(TestCase):
    obj: Image = None

    def setUp(self):
        # Open a test file from disk and upload to minIO as an image
        with open(test_file_path, 'rb') as f:
            self.obj = Image.objects.create()
            self.obj.image.save(name='audience-868074_1920.jpg', content=f)

    def tearDown(self):
        # Remove uploaded file from minIO and remove the Image entry from Django's database
        self.obj.delete()  # deletes from both locations

    def test_url_generation_works(self):
        """Accessing the value of obj.image.url"""
        val = URLValidator()
        val(self.obj.image.url)  # 1st make sure it's an URL
        self.assertTrue('audience-868074_1920' in self.obj.image.url)  # 2nd make sure our filename matches

    def test_read_image_size(self):
        self.assertEqual(self.obj.image.size, test_file_size)


class PublicAttachmentTestCase(TestCase):
    obj: PublicAttachment = None
    filename = f'public_audience-868074_1920_{int(time.time())}.jpg'  # adding unix time makes our filename unique

    def setUp(self):
        ct = ContentType.objects.get(app_label='auth', model='user')  # PublicAttachment is generic so this is needed
        with open(test_file_path, 'rb') as f:
            # noinspection PyUnresolvedReferences
            self.obj = PublicAttachment.objects.create()
            self.obj.ct = ct
            self.obj.object_id = 1  # we associate this uploaded file to user with pk=1
            self.obj.file.save(name=self.filename, content=File(f), save=True)

    def test_url_generation_works(self):
        """Accessing the value of obj.file.url"""
        val = URLValidator()
        val(self.obj.file.url)  # 1st make sure it's an URL
        self.assertTrue('public_audience-868074_1920' in self.obj.file.url)  # 2nd make sure our filename matches

    def test_read_file_size(self):
        self.assertEqual(self.obj.file_size, test_file_size)

    def test_read_file_name(self):
        self.assertEqual(self.obj.file_name, self.filename)


class PrivateAttachmentTestCase(TestCase):
    obj: PrivateAttachment = None
    filename = f'private_audience-868074_1920_{int(time.time())}.jpg'  # adding unix time makes our filename unique

    def setUp(self):
        ct = ContentType.objects.get(app_label='auth', model='user')  # PublicAttachment is generic so this is needed
        with open(test_file_path, 'rb') as f:
            # noinspection PyUnresolvedReferences
            self.obj = PublicAttachment.objects.create()
            self.obj.ct = ct
            self.obj.object_id = 1  # we associate this uploaded file to user with pk=1
            self.obj.file.save(name=self.filename, content=File(f), save=True)

    def test_url_generation_works(self):
        """Accessing the value of obj.file.url"""
        val = URLValidator()
        val(self.obj.file.url)  # 1st make sure it's an URL
        self.assertTrue('private_audience-868074_1920' in self.obj.file.url)  # 2nd make sure our filename matches

    def test_read_file_size(self):
        self.assertEqual(self.obj.file_size, test_file_size)

    def test_read_file_name(self):
        self.assertEqual(self.obj.file_name, self.filename)
