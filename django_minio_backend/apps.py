from django.apps import AppConfig
from .utils import get_setting, ConfigurationError
from .models import MinioBackend, MinioBackendStatic


__all__ = ['DjangoMinioBackendConfig', ]


class DjangoMinioBackendConfig(AppConfig):
    name = 'django_minio_backend'

    def ready(self):
        from django.core.files.storage import storages

        if not get_setting('STORAGES'):
            raise ConfigurationError("STORAGES not configured in settings. Cannot use Django minio backend.")

        # Verify STATIC storage backend
        staticfiles = storages.backends.get("staticfiles")
        if staticfiles["BACKEND"] == f"{MinioBackend.__module__}.{MinioBackendStatic.__name__}":
            # Validate configuration combinations for EXTERNAL ENDPOINT
            options = staticfiles["OPTIONS"]
            external_address = bool(options.get('MINIO_EXTERNAL_ENDPOINT'))
            external_use_https = options.get('MINIO_EXTERNAL_ENDPOINT_USE_HTTPS')
            if (external_address and external_use_https is None) or (not external_address and external_use_https):
                raise ConfigurationError(
                    'MINIO_EXTERNAL_ENDPOINT must be configured together with MINIO_EXTERNAL_ENDPOINT_USE_HTTPS')
            mbs: MinioBackendStatic = storages.create_storage(staticfiles)
            mbs.check_bucket_existence()

        # Verify MEDIA storage backend(s)
        app_path_backend_media = f"{MinioBackend.__module__}.{MinioBackend.__name__}"
        for storage_name, storage_config in storages.backends.items():
            if storage_name == "staticfiles":
                continue  # already checked
            if storage_config["BACKEND"] != app_path_backend_media:
                continue  # ignore other storage backend
            if "OPTIONS" not in storage_config:
                raise ConfigurationError("OPTIONS not configured in STORAGES. Cannot use Django minio backend.")
            options = staticfiles["OPTIONS"]
            external_address = bool(options.get('MINIO_EXTERNAL_ENDPOINT'))
            external_use_https = options.get('MINIO_EXTERNAL_ENDPOINT_USE_HTTPS')
            if (external_address and external_use_https is None) or (not external_address and external_use_https):
                raise ConfigurationError(
                    'MINIO_EXTERNAL_ENDPOINT must be configured together with MINIO_EXTERNAL_ENDPOINT_USE_HTTPS')
            mb: MinioBackend = storages.create_storage(storage_config)
            mb.validate_settings()
            # Execute on-start consistency check (if enabled)
            consistency_check_on_start = storage_config["OPTIONS"].get("MINIO_CONSISTENCY_CHECK_ON_START", False)
            if consistency_check_on_start:
                from django.core.management import call_command
                print("Executing consistency checks...")
                call_command('initialize_buckets', silenced=True)
        return True
