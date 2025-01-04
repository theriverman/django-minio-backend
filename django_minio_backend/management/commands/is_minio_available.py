from django.core.management.base import BaseCommand, CommandError
from django_minio_backend.models import MinioBackend, MinioBackendStatic
from django.core.files.storage import storages


class Command(BaseCommand):
    help = 'Checks if the configured MinIO service is available.'

    def add_arguments(self, parser):
        parser.add_argument('--silenced', action='store_true', default=False, help='No console messages')

    def handle(self, *args, **options):
        silenced = options.get('silenced')
        for storage_name, storage_config in storages.backends.items():
            if not storage_config["BACKEND"].startswith(MinioBackend.__module__):
                continue
            self.stdout.write(f"Checking MinIO availability for storage: {storage_name}\n") if not silenced else None
            m: MinioBackend|MinioBackendStatic = storages.create_storage(storage_config)
            if not (available := m.is_minio_available()):
                self.stdout.flush()
                raise CommandError(f'MinIO is NOT available at {m.base_url}\n'
                                   f'Reason: {available.details}')
            self.stdout.write(f'  * MinIO is available at {m.base_url} for {storage_name}', ending='\n') if not silenced else None
        self.stdout.flush()
