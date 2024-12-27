from django.apps import AppConfig
from .utils import get_setting, ConfigurationError
from .models import MinioBackend, MinioBackendStatic


__all__ = ['DjangoMinioBackendConfig', ]


class DjangoMinioBackendConfig(AppConfig):
    name = 'django_minio_backend'

    def ready(self):
        # Validate configuration for Django 5.1=< projects
        if STATICFILES_STORAGE := get_setting('STATICFILES_STORAGE'):
            if STATICFILES_STORAGE.endswith(MinioBackendStatic.__name__):
                raise ConfigurationError("STATICFILES_STORAGE and DEFAULT_FILE_STORAGE were replaced by STORAGES. "
                                         "See django-minio-backend's README for more information.")

        mb = MinioBackend()
        mb.validate_settings()

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
        storages = get_setting('STORAGES')
        staticfiles_backend = storages["staticfiles"]["BACKEND"]
        if staticfiles_backend.endswith(MinioBackendStatic.__name__):
            mbs = MinioBackendStatic()
            mbs.check_bucket_existence()
