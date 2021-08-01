from typing import List
from django.core.management.base import BaseCommand
from django_minio_backend.models import MinioBackend
from django_minio_backend.utils import get_setting


class Command(BaseCommand):
    help = 'Helps initializing Minio buckets by creating them and setting their policies.'

    def add_arguments(self, parser):
        parser.add_argument('--silenced', action='store_true', default=False, help='No console messages')

    def handle(self, *args, **options):
        silenced = options.get('silenced')
        self.stdout.write(f"Initializing Minio buckets...\n") if not silenced else None
        private_buckets: List[str] = get_setting("MINIO_PRIVATE_BUCKETS", [])
        public_buckets: List[str] = get_setting("MINIO_PUBLIC_BUCKETS", [])

        for bucket in [*public_buckets, *private_buckets]:
            m = MinioBackend(bucket)
            m.check_bucket_existence()
            self.stdout.write(f"Bucket ({bucket}) OK", ending='\n') if not silenced else None
            if m.is_bucket_public:  # Based on settings.py configuration
                m.set_bucket_to_public()
                self.stdout.write(
                    f"Bucket ({m.bucket}) policy has been set to public", ending='\n') if not silenced else None

        c = MinioBackend()  # Client
        for policy_tuple in get_setting('MINIO_POLICY_HOOKS', []):
            bucket, policy = policy_tuple
            c.set_bucket_policy(bucket, policy)
            self.stdout.write(
                f"Bucket ({m.bucket}) policy has been set via policy hook", ending='\n') if not silenced else None

        self.stdout.write('\nAll private & public buckets have been verified.\n', ending='\n') if not silenced else None
        self.stdout.flush()
