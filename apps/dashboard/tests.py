from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone


class DashboardStatsTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='dashboard-editor',
            password='correct-horse-battery-staple',
            role='editor',
        )

    def test_stats_require_authentication(self):
        response = self.client.get('/api/stats/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_editor_can_read_stats(self):
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['data']['total']['dynamics'], 0)

    def test_readership_complete_days_and_taxonomy_weight(self):
        from apps.dynamic.models import Dynamic
        from apps.category.models import Category
        from apps.access_log.models import AccessLog
        category = Category.objects.create(name='阅读主题')
        article = Dynamic.objects.create(author=self.user, title='热文', content='内容', status='published', view_count=1320, category=category)
        Dynamic.objects.create(author=self.user, title='草稿', content='内容', status='draft', view_count=9999)
        for path in [f'/api/blog/dynamics/{article.pk}/', f'/api/blog/dynamics/{article.pk}/', '/api/stats/', '/api/blog/dynamics/recent/']:
            AccessLog.objects.create(ip_address='192.168.1.1', user_agent='browser', method='GET', path=path, status_code=200)
        self.client.force_authenticate(self.user)
        data = self.client.get('/api/stats/').data['data']
        self.assertEqual(len(data['daily']), 7)
        self.assertEqual(sum(row['count'] for row in data['daily']), 1)
        self.assertEqual(data['visits']['pv'], 2)
        self.assertEqual(data['visits']['uv'], 1)
        self.assertEqual(data['visits']['bounce_rate'], 0)
        self.assertEqual(data['categories'][0]['views'], 1320)
        self.assertEqual(data['hot_articles'][0]['id'], article.pk)
        self.assertEqual(sum(row['pv'] for row in data['daily']), 2)

    def test_daily_publishing_uses_local_calendar_day(self):
        from datetime import datetime, timezone as dt_timezone
        from apps.dynamic.models import Dynamic

        article = Dynamic.objects.create(
            author=self.user,
            title='北京时间发布',
            content='内容',
            status='published',
        )
        # 16:30 UTC is 00:30 on the next day in Asia/Shanghai.
        Dynamic.objects.filter(pk=article.pk).update(
            created_at=datetime(2026, 9, 8, 16, 30, tzinfo=dt_timezone.utc),
        )
        self.client.force_authenticate(self.user)

        with timezone.override('Asia/Shanghai'):
            response = self.client.get('/api/stats/')

        daily = response.data['data']['daily']
        self.assertEqual(sum(row['count'] for row in daily), 1)
        self.assertEqual(
            next(row['count'] for row in daily if row['day'] == '2026-09-09'),
            1,
        )

    def test_local_day_counter_converts_utc_values_in_application(self):
        from datetime import datetime, timezone as dt_timezone
        from apps.dashboard.views import count_local_days

        values = [
            datetime(2026, 9, 8, 16, 30, tzinfo=dt_timezone.utc),
            datetime(2026, 9, 8, 15, 59, tzinfo=dt_timezone.utc),
        ]

        self.assertEqual(
            count_local_days(values, 'Asia/Shanghai'),
            {'2026-09-08': 1, '2026-09-09': 1},
        )

    def test_security_excludes_old_activity_and_whitelist(self):
        from apps.access_log.models import AccessLog, IpSecurityRule
        from django.utils import timezone
        from datetime import timedelta
        for ip in ['192.168.1.1', '192.168.1.2']:
            AccessLog.objects.bulk_create([AccessLog(ip_address=ip, method='POST', path='/api/auth/login/', status_code=401) for _ in range(8)])
        IpSecurityRule.objects.create(target='192.168.1.1', rule_type='whitelist')
        old = AccessLog.objects.create(ip_address='192.168.1.3', method='GET', path='/old', status_code=200)
        AccessLog.objects.filter(pk=old.pk).update(created_at=timezone.now()-timedelta(days=8))
        self.client.force_authenticate(self.user)
        data = self.client.get('/api/stats/').data['data']['security']
        self.assertEqual(data['unique_ips'], 2)
        self.assertEqual(data['high'], 1)
        self.assertEqual([row['ip_address'] for row in data['top_ips']], ['192.168.1.2'])


class SystemHealthTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='health-editor',
            password='PreviewA1!pass',
            role='admin',
        )

    def test_health_requires_authentication_and_returns_minimal_status(self):
        response = self.client.get('/api/system/health/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/system/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'ok')
        self.assertIn('checked_at', response.data['data'])
