import logging
from django.core.files.storage import storages
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db.models import FileField, ImageField
from minio.deleteobjects import DeleteObject
from django_minio_backend.models import MinioBackend, MinioBackendStatic
from collections import defaultdict

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete orphaned files from Minio storage that are no longer referenced in the database and identify database references to missing Minio files"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", dest="dry_run", help="Run without actually deleting files", )
        parser.add_argument("--check-missing", action="store_true", dest="check_missing",
            help="Check for database references to missing Minio files", )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        check_missing = options.get("check_missing", False)

        # initialise storages where MinioBackend is the backend
        storage_instances = []
        for storage_name, storage_config in storages.backends.items():
            if storage_config["BACKEND"].endswith(MinioBackendStatic.__name__):
                continue
            if not storage_config["BACKEND"].startswith(MinioBackend.__module__):
                continue
            if not storage_config["BACKEND"].endswith(MinioBackend.__name__):
                continue
            # Initialise storage driver by storage_name
            storage_instances.append(MinioBackend(storage_name=storage_name))

        # Get all objects from FileField and ImageField instances backed by MinioBackend
        db_files_by_model, db_files = self._collect_file_fields()

        # Part 1: Delete orphaned files from Minio
        for s in storage_instances:
            self._clean_orphaned_files(s, db_files, dry_run)
            # Part 2: Check for missing files in Minio that are referenced in the database
            if check_missing:
                self._check_missing_files(s, db_files_by_model)

    def _clean_orphaned_files(self, storage: MinioBackend, db_files: set, dry_run: bool):
        """Delete orphaned files from Minio that are not referenced in the database"""
        total_deleted = 0

        for bucket_name in [storage.bucket, *storage.PRIVATE_BUCKETS, *storage.PUBLIC_BUCKETS]:
            # Set the current bucket for operations
            storage._BUCKET_NAME = bucket_name

            # Get all objects in the bucket
            try:
                objects = storage.client.list_objects(bucket_name=bucket_name, recursive=True)

                # Create a list to collect objects to delete
                delete_objects = []

                for obj in objects:
                    object_name = obj.object_name

                    # Check if the object is referenced in the database
                    if object_name not in db_files:
                        delete_objects.append(DeleteObject(object_name))
                        self.stdout.write(f"Found orphaned file: {bucket_name}/{object_name}")

                # Delete orphaned objects in bulk
                if delete_objects:
                    if not dry_run:
                        errors = storage.client.remove_objects(bucket_name, delete_objects)

                        # Check for errors during deletion
                        error_count = 0
                        for error in errors:
                            error_count += 1
                            logger.error(f"Error deleting {error.object_name}: {error.message}")

                        successful_deletions = len(delete_objects) - error_count
                        total_deleted += successful_deletions

                        self.stdout.write(
                            self.style.SUCCESS(f"Successfully deleted {successful_deletions} orphaned files from bucket '{bucket_name}'"))
                        if error_count > 0:
                            self.stdout.write(self.style.WARNING(f"Failed to delete {error_count} files from bucket '{bucket_name}'"))
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"Would delete {len(delete_objects)} orphaned files from bucket '{bucket_name}' (dry run)"))
                        total_deleted += len(delete_objects)
                else:
                    self.stdout.write(f"No orphaned files found in bucket '{bucket_name}'")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing bucket '{bucket_name}': {str(e)}"))

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Would delete {total_deleted} orphaned files in total (dry run)"))
        else:
            if total_deleted > 0:
                self.stdout.write(self.style.SUCCESS(f"Successfully deleted {total_deleted} orphaned files in total"))
            else:
                self.stdout.write(self.style.SUCCESS(f"{total_deleted} orphaned files were found"))

    def _check_missing_files(self, storage: MinioBackend, db_files_by_model):
        """Check for database references to files that don't exist in Minio"""
        self.stdout.write(self.style.NOTICE("\nChecking for database references to missing Minio files..."))

        missing_files_count = 0

        for model, fields in db_files_by_model.items():
            for field_name, objects in fields.items():
                for obj_id, file_path in objects:
                    parts = file_path.split("/")
                    bucket, object_name = parts[0], "/".join(parts[1:])
                    # Set the current bucket for operations
                    storage._BUCKET_NAME = bucket

                    # Check if the file exists in Minio
                    if not storage.exists(object_name):
                        # File doesn't exist in Minio
                        missing_files_count += 1
                        model_name = model._meta.label
                        self.stdout.write(self.style.WARNING(f"Missing file in Minio: {bucket}/{object_name} "
                                                             f"referenced by {model_name} (id={obj_id}, field={field_name})"))

        if missing_files_count == 0:
            self.stdout.write(self.style.SUCCESS("No missing files found in Minio that are referenced in the database"))
        else:
            self.stdout.write(self.style.WARNING(f"Found {missing_files_count} database references to missing Minio files"))

    def _collect_file_fields(self):
        """Collect file fields across the Django project"""

        # Dictionary to store file references by model and field
        db_files_by_model = defaultdict(lambda: defaultdict(list))
        db_files = set()
        file_fields_count = 0

        all_models = apps.get_models()

        # Get all files from the database
        for model in all_models:
            file_fields = []
            for field in model._meta.fields:
                if isinstance(field, (FileField, ImageField)):
                    if isinstance(field.storage, MinioBackend):
                        file_fields.append(field.name)
                        file_fields_count += 1

            # Only retrieve the models which have file fields
            if file_fields:
                for field_name in file_fields:
                    # Get all objects with non-empty file fields
                    objects = model.objects.exclude(**{f"{field_name}__isnull": True})

                    # Store file paths by model and field for checking missing files later
                    for obj in objects:
                        if file_path := getattr(obj, field_name):
                            bucket = file_path.storage.bucket
                            file_path_str = str(file_path)
                            db_files.add(file_path_str)
                            db_files_by_model[model][field_name].append((obj.pk, f"{bucket}/{file_path_str}"))
                    db_files.discard("")

        self.stdout.write(f"Found {file_fields_count} file/image fields across all models")
        self.stdout.write(f"Found {len(db_files)} files referenced in the database")

        return db_files_by_model, db_files
