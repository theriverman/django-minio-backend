from django.test import TestCase

from DjangoExampleApplication.models import Image


class AnimalTestCase(TestCase):
    def setUp(self):
        with open('DjangoExampleApplication/assets/audience-868074_1920.jpg', 'rb') as f:
            img = Image.objects.create()
            img.image.save(name='audience-868074_1920.jpg', content=f)

    def test_url_generation_works(self):
        """Animals that can speak are correctly identified"""
        img = Image.objects.last()
        self.assertTrue('audience-868074_1920' in img.image.url)
