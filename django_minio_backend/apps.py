from django.apps import AppConfig
from .utils import get_setting, ConfigurationError
from .models import MinioBackendStatic


__all__ = ['DjangoMinioBackendConfig', ]


class DjangoMinioBackendConfig(AppConfig):
    name = 'django_minio_backend'

    def ready(self):
        consistency_check_on_start = get_setting('MINIO_CONSISTENCY_CHECK_ON_START', False)
        if consistency_check_on_start:
            from django.core.management import call_command
            print("Executing consistency checks...")
            call_command('initialize_buckets', silenced=True)

        # Validate configuration combinations for EXTERNAL ENDPOINT
        external_address = bool(get_setting('MINIO_EXTERNAL_ENDPOINT'))
        external_use_https = get_setting('MINIO_EXTERNAL_ENDPOINT_USE_HTTPS')
        if (external_address and external_use_https is None) or (not external_address and external_use_https):
            raise ConfigurationError('MINIO_EXTERNAL_ENDPOINT must be configured together with MINIO_EXTERNAL_ENDPOINT_USE_HTTPS')

        # Validate static storage and default storage configurations
        staticfiles_storage: str = get_setting('STATICFILES_STORAGE')
        if staticfiles_storage.endswith(MinioBackendStatic.__name__):
            mbs = MinioBackendStatic()
            mbs.check_bucket_existence()
