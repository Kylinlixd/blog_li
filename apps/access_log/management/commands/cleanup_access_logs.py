import os
from django.core.management.base import BaseCommand
from apps.access_log.models import AccessLog


class Command(BaseCommand):
    help = 'Delete access logs older than the configured retention window.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=int(os.getenv('ACCESS_LOG_RETENTION_DAYS', '90')))

    def handle(self, *args, **options):
        deleted, _ = AccessLog.purge_expired(options['days'])
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} expired access logs.'))
