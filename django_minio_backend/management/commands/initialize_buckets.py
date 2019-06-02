from django.core.management.base import BaseCommand, no_translations
from django_minio_backend.models import MinioBackend


class Command(BaseCommand):
    help = 'Helps initializing Minio buckets by creating them and setting their policies.'

    @no_translations
    def handle(self, *args, **options):
        self.stdout.write(f"Initializing Minio buckets...")
        m = MinioBackend()
        m.check_bucket_existences()
        self.stdout.write(f"Private and public backends have been checked/created")
        m.set_bucket_to_public(bucket_name=m.MINIO_PUBLIC_BUCKET_NAME)
        self.stdout.write(f"Public backend policy have been updated")
