from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from .models import AccessLog
from .device import parse_user_agent
from django.core.management import call_command
from datetime import timedelta
from django.utils import timezone

from apps.access_log.models import IpSecurityRule
from apps.access_log.profile import build_ip_profile, classify_ip
from apps.access_log.rules import precedence_for_ip


class AccessLogTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='log-admin', password='safe-password-123', is_staff=True)

    def test_api_request_records_forwarded_ip(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/stats/', HTTP_X_FORWARDED_FOR='203.0.113.8, 10.0.0.1', HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(AccessLog.objects.filter(path='/api/stats/', ip_address='203.0.113.8', user=self.user).exists())
        log = AccessLog.objects.get(path='/api/stats/', ip_address='203.0.113.8', user=self.user)
        self.assertEqual((log.device_type, log.device_model), ('mobile', 'iPhone'))

    def test_device_parser_identifies_common_models(self):
        self.assertEqual(parse_user_agent('Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/UP1A)'), ('mobile', 'Pixel 8'))
        self.assertEqual(parse_user_agent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'), ('computer', 'Mac 电脑'))

    def test_cleanup_command_removes_only_expired_rows(self):
        expired = AccessLog.objects.create(ip_address='192.0.2.1', method='GET', path='/old', status_code=200)
        AccessLog.objects.filter(pk=expired.pk).update(created_at=timezone.now() - timedelta(days=120))
        AccessLog.objects.create(ip_address='192.0.2.2', method='GET', path='/new', status_code=200)
        call_command('cleanup_access_logs', days=90)
        self.assertFalse(AccessLog.objects.filter(path='/old').exists())
        self.assertTrue(AccessLog.objects.filter(path='/new').exists())

    def test_logs_are_staff_only(self):
        response = self.client.get('/api/access-logs/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_can_filter_logs_by_ip_status_and_path(self):
        AccessLog.objects.create(ip_address='203.0.113.8', method='GET', path='/api/stats/', status_code=200)
        AccessLog.objects.create(ip_address='198.51.100.2', method='GET', path='/api/auth/info/', status_code=401)
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/access-logs/', {'ip': '203.0.113.8', 'status': '2', 'path': 'stats'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 1)

    def test_authenticated_management_user_can_read_logs(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/access-logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AccessLogProfileTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='log-security-admin',
            password='safe-password-123',
            is_staff=True,
        )

    def test_classify_ip_identifies_scope_and_version(self):
        self.assertEqual(classify_ip('192.168.1.8')['scope'], 'private')
        self.assertEqual(classify_ip('192.168.1.8')['version'], 4)
        self.assertEqual(classify_ip('127.0.0.1')['scope'], 'loopback')
        self.assertEqual(classify_ip('2001:db8::1')['version'], 6)
        self.assertEqual(classify_ip('bad ip')['scope'], 'unknown')

    def test_profile_flags_authentication_failure_burst(self):
        now = timezone.now()
        for _ in range(8):
            AccessLog.objects.create(
                ip_address='198.51.100.8',
                method='POST',
                path='/api/auth/login/',
                status_code=401,
                created_at=now,
            )

        profile = build_ip_profile('198.51.100.8', now=timezone.now())

        self.assertEqual(profile['behavior']['total_requests'], 8)
        self.assertEqual(profile['risk_level'], 'high')
        self.assertIn('认证失败集中', profile['risk_reasons'])


class AccessLogSecurityApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='security-admin',
            password='safe-password-123',
            is_staff=True,
        )
        AccessLog.objects.create(ip_address='198.51.100.9', method='GET', path='/api/stats/', status_code=200)

    def test_profiles_are_management_only(self):
        response = self.client.get('/api/access-logs/profiles/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_can_browse_profiles_and_details(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/access-logs/profiles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 1)
        self.assertEqual(response.data['data']['list'][0]['ip_address'], '198.51.100.9')

        detail = self.client.get('/api/access-logs/profile/', {'ip': '198.51.100.9'})
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['data']['ip_address'], '198.51.100.9')

    def test_rule_lifecycle_and_enforcement(self):
        self.client.force_authenticate(self.user)
        create = self.client.post('/api/access-log-rules/', {
            'target': '198.51.100.20',
            'rule_type': 'ban',
            'attack_level': 'high',
            'is_permanent': True,
            'reason': '持续扫描',
        }, format='json')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        rule_id = create.data['id']

        self.client.force_authenticate(None)
        blocked = self.client.get('/api/stats/', HTTP_X_FORWARDED_FOR='198.51.100.20')
        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.user)
        revoked = self.client.post(f'/api/access-log-rules/{rule_id}/revoke/')
        self.assertEqual(revoked.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(None)
        allowed = self.client.get('/api/blog/dynamics/recent/?limit=1', HTTP_X_FORWARDED_FOR='198.51.100.20')
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)

    def test_rate_limit_returns_retry_after(self):
        self.client.force_authenticate(self.user)
        create = self.client.post('/api/access-log-rules/', {
            'target': '203.0.113.50',
            'rule_type': 'rate_limit',
            'requests': 2,
            'window_seconds': 60,
            'reason': '防刷',
        }, format='json')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        self.client.force_authenticate(None)
        rate_rule = precedence_for_ip('203.0.113.50')
        self.assertIsNotNone(rate_rule)
        self.assertEqual((rate_rule.rule_type, rate_rule.requests, rate_rule.window_seconds), ('rate_limit', 2, 60))

        first = self.client.get('/api/blog/dynamics/recent/?limit=1', HTTP_X_FORWARDED_FOR='203.0.113.50')
        second = self.client.get('/api/blog/dynamics/recent/?limit=1', HTTP_X_FORWARDED_FOR='203.0.113.50')
        third = self.client.get('/api/blog/dynamics/recent/?limit=1', HTTP_X_FORWARDED_FOR='203.0.113.50')
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(third.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(third['Retry-After'], '60')

    def test_whitelist_has_highest_precedence(self):
        self.client.force_authenticate(self.user)
        self.client.post('/api/access-log-rules/', {
            'target': '203.0.113.60',
            'rule_type': 'ban',
            'is_permanent': True,
            'reason': '临时',
        }, format='json')
        self.client.post('/api/access-log-rules/', {
            'target': '203.0.113.60',
            'rule_type': 'whitelist',
            'reason': '信任',
        }, format='json')
        self.client.force_authenticate(None)

        response = self.client.get('/api/blog/dynamics/recent/?limit=1', HTTP_X_FORWARDED_FOR='203.0.113.60')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
