from typing import List
from django.core.management.base import BaseCommand
from django_minio_backend.models import MinioBackend
from django_minio_backend.utils import get_setting


class Command(BaseCommand):
    help = 'Helps initializing Minio buckets by creating them and setting their policies.'

    def handle(self, *args, **options):
        self.stdout.write(f"Initializing Minio buckets...\n")
        private_buckets: List[str] = get_setting("MINIO_PRIVATE_BUCKETS", [])
        public_buckets: List[str] = get_setting("MINIO_PUBLIC_BUCKETS", [])

        # TODO: This part may become slow if lots of buckets are declared. Consider using asyncio here!
        for bucket in [*public_buckets, *private_buckets]:
            m = MinioBackend(bucket)
            m.check_bucket_existence()
            self.stdout.write(f"Bucket ({bucket}) OK", ending='\n')
            if m.is_bucket_public:  # Based on settings.py configuration
                m.set_bucket_to_public()
                self.stdout.write(f"Bucket ({m.bucket}) policy has been set to public", ending='\n')

        c = MinioBackend('')  # Client
        for policy_tuple in get_setting('MINIO_POLICY_HOOKS', []):
            bucket, policy = policy_tuple
            c.set_bucket_policy(bucket, policy)
            self.stdout.write(f"Bucket ({m.bucket}) policy has been set via policy hook", ending='\n')

        self.stdout.write('\nAll private & public buckets have been verified.\n', ending='\n')
        self.stdout.flush()
