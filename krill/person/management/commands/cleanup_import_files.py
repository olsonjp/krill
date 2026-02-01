"""
Management command to clean up old temporary import files.
Run this periodically (e.g., via cron) to prevent disk space issues.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import os
import json
import logging

from person.utils import get_upload_temp_dir

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up old temporary import files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Delete files older than this many hours (default: 24)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']

        temp_dir = get_upload_temp_dir()
        cutoff_time = timezone.now() - timedelta(hours=hours)

        deleted_files = 0
        deleted_size = 0
        errors = 0

        self.stdout.write(f"Cleaning up import files older than {hours} hours...")
        self.stdout.write(f"Cutoff time: {cutoff_time}")

        if not os.path.exists(temp_dir):
            self.stdout.write(f"Temp directory {temp_dir} does not exist")
            return

        # Look for user-specific import directories
        for item in os.listdir(temp_dir):
            if item.startswith('imports_'):
                user_temp_dir = os.path.join(temp_dir, item)
                if os.path.isdir(user_temp_dir):
                    self.stdout.write(f"Processing {user_temp_dir}")

                    # Process files in this directory
                    for filename in os.listdir(user_temp_dir):
                        if filename.endswith('.csv'):
                            import_id = filename[:-4]  # Remove .csv extension
                            csv_path = os.path.join(user_temp_dir, filename)
                            meta_path = os.path.join(user_temp_dir, f'{import_id}.meta')

                            try:
                                # Check if metadata file exists
                                if not os.path.exists(meta_path):
                                    self.stdout.write(f"  Missing metadata for {filename}, deleting...")
                                    if not dry_run:
                                        os.remove(csv_path)
                                    deleted_files += 1
                                    continue

                                # Read metadata to check timestamp
                                with open(meta_path, 'r') as f:
                                    metadata = json.load(f)

                                file_timestamp = timezone.datetime.fromisoformat(metadata['timestamp'].replace('Z', '+00:00'))

                                if file_timestamp < cutoff_time:
                                    file_size = os.path.getsize(csv_path)
                                    self.stdout.write(f"  Deleting old file: {filename} (created: {file_timestamp})")

                                    if not dry_run:
                                        os.remove(csv_path)
                                        os.remove(meta_path)

                                    deleted_files += 1
                                    deleted_size += file_size

                            except Exception as e:
                                self.stdout.write(f"  Error processing {filename}: {e}")
                                errors += 1
                                logger.error(f"Error processing import file {filename}: {e}")

        # Summary
        self.stdout.write(f"\nCleanup complete:")
        self.stdout.write(f"  Files deleted: {deleted_files}")
        self.stdout.write(f"  Space freed: {deleted_size / 1024 / 1024:.2f} MB")
        self.stdout.write(f"  Errors: {errors}")

        if dry_run:
            self.stdout.write("  (DRY RUN - no files were actually deleted)")
