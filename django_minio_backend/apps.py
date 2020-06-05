from django.apps import AppConfig
from .utils import get_setting


__all__ = ['DjangoMinioBackendConfig', ]


class DjangoMinioBackendConfig(AppConfig):
    name = 'django_minio_backend'

    def ready(self):
        consistency_check_on_start = get_setting('MINIO_CONSISTENCY_CHECK_ON_START', False)
        if consistency_check_on_start:
            from django.core.management import call_command
            print("Executing consistency checks...")
            call_command('initialize_buckets', silenced=True)
