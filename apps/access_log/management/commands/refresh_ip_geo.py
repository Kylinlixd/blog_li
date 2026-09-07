import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.access_log.models import AccessLog, IpGeoCache
from apps.access_log.profile import classify_ip
from apps.access_log.geo import lookup_geo


class Command(BaseCommand):
    help = 'Refresh distinct historical public IP ownership using 360; preserve previous data on failure.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Refresh even unexpired cached IPs')
        parser.add_argument('--delay', type=float, default=0.2)

    def handle(self, *args, **options):
        if options['delay'] < 0:
            raise CommandError('delay 必须大于等于 0')
        ips = AccessLog.objects.exclude(ip_address__isnull=True).order_by().values_list('ip_address', flat=True).distinct()
        fresh = set(IpGeoCache.objects.filter(expires_at__gt=timezone.now(), lookup_ok=True).values_list('ip_address', flat=True))
        success = failed = skipped = 0
        for ip in ips.iterator(chunk_size=500):
            if not classify_ip(ip)['is_public'] or (not options['all'] and ip in fresh):
                skipped += 1
                continue
            lookup_geo(ip, force=True)
            if IpGeoCache.objects.filter(ip_address=ip, lookup_ok=True).exists():
                success += 1
            else:
                failed += 1
                self.stderr.write(f'查询失败，保留原归属：{ip}')
            if options['delay']:
                time.sleep(options['delay'])
        self.stdout.write(f'成功 {success}，失败 {failed}，跳过 {skipped}')
        if failed:
            raise CommandError('部分 IP 查询失败，可重跑以重试失败项')
