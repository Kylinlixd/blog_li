from datetime import datetime, time, timedelta
from collections import Counter
from zoneinfo import ZoneInfo

from django.db.models import Count, Sum, Q
from django.db.models.functions import Coalesce
from django.conf import settings
from django.utils import timezone
from apps.user.permissions import IsContentEditor
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.category.models import Category
from apps.comment.models import Comment
from apps.dynamic.models import Dynamic
from apps.tag.models import Tag
from apps.access_log.models import AccessLog
from apps.access_log.profile import build_ip_profiles


def count_local_days(values, timezone_name):
    """Count aware datetimes by local calendar day without DB timezone functions."""
    target_zone = ZoneInfo(timezone_name)
    counts = Counter()
    for value in values:
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone=timezone.utc)
        counts[timezone.localtime(value, target_zone).date().isoformat()] += 1
    return dict(counts)


class StatsView(APIView):
    permission_classes = [IsContentEditor]

    def get(self, request):
        today = timezone.localdate()
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        start = timezone.make_aware(datetime.combine(days[0], time.min))
        now = timezone.now()
        published = Dynamic.objects.filter(status='published')
        published_values = published.filter(
            created_at__gte=start,
            created_at__lte=now,
        ).order_by().values_list('created_at', flat=True).iterator(chunk_size=2000)
        counts = count_local_days(published_values, settings.TIME_ZONE)
        logs = AccessLog.objects.filter(created_at__gte=start, created_at__lte=now)
        readings = logs.filter(method='GET', status_code__gte=200, status_code__lt=300,
                               path__regex=r'^/api/blog/dynamics/[0-9]+/$')
        pv_by_day = Counter()
        visitors = set()
        sessions = []
        previous = {}
        # The existing logs have no session ID. Estimate sessions by IP+UA and a 30-minute gap.
        for row in readings.order_by('created_at').values('created_at', 'ip_address', 'user_agent'):
            pv_by_day[timezone.localtime(row['created_at']).date()] += 1
            if not row['ip_address']:
                continue
            visitor = (row['ip_address'], row['user_agent'])
            visitors.add(visitor)
            last = previous.get(visitor)
            if last is None or row['created_at'] - last[0] >= timedelta(minutes=30):
                sessions.append(1)
                index = len(sessions) - 1
            else:
                index = last[1]
                sessions[index] += 1
            previous[visitor] = (row['created_at'], index)
        pv = sum(pv_by_day.values())
        ips = list(logs.exclude(ip_address__isnull=True).order_by().values_list('ip_address', flat=True).distinct())
        security = dict(unique_ips=len(ips), medium=0, high=0, critical=0, top_ips=[])
        requests_by_ip = dict(logs.values('ip_address').annotate(count=Count('id')).values_list('ip_address', 'count'))
        for profile in build_ip_profiles(ips, now=now, since=start):
            ip = profile['ip_address']
            level = profile['risk_level']
            if level in ('medium', 'high', 'critical'):
                security[level] += 1
                security['top_ips'].append(dict(ip_address=ip, risk_level=level, risk_score=profile['risk_score'], requests=requests_by_ip[ip]))
        security['top_ips'] = sorted(security['top_ips'], key=lambda row: (-row['risk_score'], -row['requests'], row['ip_address']))[:3]

        def taxonomy(model):
            return list(model.objects.annotate(
                dynamic_count=Count('dynamics', filter=Q(dynamics__status='published')),
                views=Coalesce(Sum('dynamics__view_count', filter=Q(dynamics__status='published')), 0),
            ).filter(dynamic_count__gt=0).order_by('-views', '-dynamic_count', 'name').values('name', 'dynamic_count', 'views')[:5])

        hot = list(published.annotate(comment_count=Count('comments', distinct=True)).order_by('-view_count', '-created_at')
                   .values('id', 'title', 'view_count', 'comment_count')[:5])
        return Response({'code': 200, 'message': 'success', 'data': {
            'total': dict(dynamics=Dynamic.objects.count(), categories=Category.objects.count(), tags=Tag.objects.count(), comments=Comment.objects.count()),
            'daily': [dict(day=day.isoformat(), count=counts.get(day.isoformat(), 0), pv=pv_by_day.get(day, 0)) for day in days],
            'range': dict(start=days[0].isoformat(), end=days[-1].isoformat(), timezone=settings.TIME_ZONE),
            'categories': taxonomy(Category), 'tags': taxonomy(Tag),
            'access': dict(requests=logs.count(), unique_ips=len(ips)),
            'visits': dict(pv=pv, uv=len(visitors), average=round(pv / 7, 1),
                           bounce_rate=round(sum(n == 1 for n in sessions) / len(sessions) * 100, 1) if sessions else None,
                           bounce_estimated=True),
            'hot_articles': hot, 'security': security,
        }})
