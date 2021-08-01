from django.core.management.base import BaseCommand, CommandError
from django_minio_backend.models import MinioBackend


class Command(BaseCommand):
    help = 'Checks if the configured MinIO service is available.'

    def add_arguments(self, parser):
        parser.add_argument('--silenced', action='store_true', default=False, help='No console messages')

    def handle(self, *args, **options):
        m = MinioBackend()  # use default storage
        silenced = options.get('silenced')
        self.stdout.write(f"Checking the availability of MinIO at {m.base_url}\n") if not silenced else None

        available = m.is_minio_available()
        if not available:
            self.stdout.flush()
            raise CommandError(f'MinIO is NOT available at {m.base_url}\n'
                               f'Reason: {available.details}')

        self.stdout.write(f'MinIO is available at {m.base_url}', ending='\n') if not silenced else None
        self.stdout.flush()
