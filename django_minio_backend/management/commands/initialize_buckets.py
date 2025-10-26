from typing import List

from django.core.files.storage import storages
from django.core.management.base import BaseCommand
from django_minio_backend.models import MinioBackend, MinioBackendStatic
from django_minio_backend.utils import get_setting


class Command(BaseCommand):
    help = 'Helps initializing Minio buckets by creating them and setting their policies.'

    def add_arguments(self, parser):
        parser.add_argument('--silenced', action='store_true', default=False, help='No console messages')

    def handle(self, *args, **options):
        silenced = options.get('silenced')
        self.stdout.write(f"Initializing Minio buckets...\n") if not silenced else None
        i = 0
        for storage_name, storage_config in storages.backends.items():
            if not storage_config["BACKEND"].startswith(MinioBackend.__module__):
                continue
            self.stdout.write(f"Initialising buckets for storage backend: {storage_name}\n") if not silenced else None
            if storage_config["BACKEND"].endswith(MinioBackendStatic.__name__):
                i += 1
                ms: MinioBackendStatic = storages.create_storage(storage_config)
                ms.check_bucket_existence()
                ms.set_bucket_to_public()  # enforce a public static bucket
                continue
            if storage_config["BACKEND"].endswith(MinioBackend.__name__):
                i += 1
                public_buckets = storage_config["OPTIONS"].get("MINIO_PUBLIC_BUCKETS", list())
                private_buckets = storage_config["OPTIONS"].get("MINIO_PRIVATE_BUCKETS", list())
                # MINIO_DEFAULT_BUCKET
                if (b := storage_config["OPTIONS"].get("MINIO_DEFAULT_BUCKET")) and b not in [*public_buckets, *private_buckets]:
                    private_buckets.append(b)  # DEFAULT BUCKET IS PRIVATE BY DEFAULT
                for bucket in [*public_buckets, *private_buckets]:
                    mm: MinioBackend = MinioBackend(bucket_name=bucket, storage_name=storage_name, )
                    mm.check_bucket_existence()
                    self.stdout.write(f"Bucket ({bucket}) OK", ending='\n') if not silenced else None
                    if mm.is_bucket_public:  # Based on settings.py configuration
                        mm.set_bucket_to_public()
                        self.stdout.write(
                            f"Bucket ({mm.bucket}) policy has been set to public", ending='\n') if not silenced else None
                    for policy_tuple in storage_config["OPTIONS"].get("MINIO_POLICY_HOOKS", list()):
                        bucket, policy = policy_tuple
                        mm.set_bucket_policy(bucket, policy)
                        self.stdout.write(
                            f"Bucket ({bucket})'s policy has been set via policy hook",
                            ending='\n') if not silenced else None
                continue
        self.stdout.write('\nAll buckets have been verified.\n', ending='\n') if not silenced else None
        self.stdout.flush()
