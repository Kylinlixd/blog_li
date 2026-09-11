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

    def _create_spread_logs(self, ip, total, failed, now, failed_status=500):
        rows = []
        for index in range(total):
            rows.append(AccessLog(
                ip_address=ip,
                method='GET',
                path='/api/health/',
                status_code=failed_status if index < failed else 200,
                created_at=now - timedelta(minutes=index * 3),
            ))
        AccessLog.objects.bulk_create(rows)
        for index, row in enumerate(rows):
            row.created_at = now - timedelta(minutes=index * 3)
        AccessLog.objects.bulk_update(rows, ['created_at'])

    def test_behavior_anomaly_uses_window_failure_count_and_rate(self):
        now = timezone.now()
        self._create_spread_logs('198.51.100.20', 68, 66, now, failed_status=400)
        profile = build_ip_profile('198.51.100.20', now=now)

        risk = profile['behavior']['risk']
        self.assertEqual((risk['total_requests'], risk['failed_requests']), (68, 66))
        self.assertEqual(risk['error_rate'], 97.1)
        self.assertEqual(risk['anomaly_level'], 'high')
        self.assertEqual(profile['risk_level'], 'high')
        self.assertGreaterEqual(profile['risk_score'], 50)

    def test_server_errors_mark_anomaly_without_ip_security_score(self):
        now = timezone.now()
        self._create_spread_logs('198.51.100.21', 68, 66, now)
        profile = build_ip_profile('198.51.100.21', now=now)

        risk = profile['behavior']['risk']
        self.assertEqual(risk['client_errors'], 0)
        self.assertEqual(risk['server_errors'], 66)
        self.assertEqual(risk['anomaly_level'], 'high')
        self.assertEqual(profile['risk_level'], 'low')
        self.assertEqual(profile['risk_score'], 0)
        self.assertTrue(any('服务端错误偏多，建议排查服务' in reason for reason in risk['anomaly_reasons']))
        self.assertIn('未发现明显IP安全风险', profile['risk_reasons'])

    def test_mixed_failures_report_each_error_class_with_its_own_rate(self):
        now = timezone.now()
        self._create_spread_logs('198.51.100.32', 68, 65, now, failed_status=500)
        first = AccessLog.objects.filter(ip_address='198.51.100.32').order_by('id').first()
        first.status_code = 400
        first.save(update_fields=['status_code'])

        risk = build_ip_profile('198.51.100.32', now=now)['behavior']['risk']
        self.assertEqual((risk['client_errors'], risk['server_errors']), (1, 64))
        self.assertEqual(risk['anomaly_level'], 'high')
        self.assertFalse(any('客户端错误偏多' in reason or '客户端错误集中' in reason for reason in risk['anomaly_reasons']))
        self.assertTrue(any('服务端错误偏多，建议排查服务（失败 64/68' in reason for reason in risk['anomaly_reasons']))

    def test_client_error_floor_applies_after_other_security_signals(self):
        now = timezone.now()
        AccessLog.objects.bulk_create([
            AccessLog(
                ip_address='198.51.100.33',
                method='GET',
                path=f'/api/paths/{index}/',
                status_code=400 if index < 10 else 200,
                created_at=now,
            )
            for index in range(30)
        ])
        AccessLog.objects.filter(ip_address='198.51.100.33').update(created_at=now - timedelta(hours=2))

        profile = build_ip_profile('198.51.100.33', now=now)
        self.assertEqual(profile['behavior']['risk']['anomaly_level'], 'medium')
        self.assertEqual(profile['risk_score'], 25)

    def test_behavior_anomaly_thresholds_require_count_and_ratio(self):
        now = timezone.now()
        cases = {
            '198.51.100.22': (9, 10, 'normal'),
            '198.51.100.23': (10, 34, 'normal'),
            '198.51.100.24': (10, 33, 'medium'),
            '198.51.100.25': (29, 59, 'medium'),
            '198.51.100.26': (30, 60, 'high'),
            '198.51.100.27': (99, 123, 'high'),
            '198.51.100.28': (100, 125, 'critical'),
        }
        for ip, (failed, total, expected) in cases.items():
            self._create_spread_logs(ip, total, failed, now)

        for ip, (_, _, expected) in cases.items():
            self.assertEqual(build_ip_profile(ip, now=now)['behavior']['risk']['anomaly_level'], expected)

    def test_behavior_window_is_distinct_from_historical_total_and_empty_window(self):
        now = timezone.now()
        self._create_spread_logs('198.51.100.29', 100, 100, now - timedelta(days=8))
        AccessLog.objects.filter(ip_address='198.51.100.29').update(created_at=now - timedelta(days=8))
        self._create_spread_logs('198.51.100.29', 3, 1, now)
        profile = build_ip_profile('198.51.100.29', now=now)
        risk = profile['behavior']['risk']
        self.assertEqual(profile['behavior']['total_requests'], 103)
        self.assertEqual((risk['total_requests'], risk['failed_requests']), (3, 1))
        self.assertEqual(risk['anomaly_level'], 'normal')

        empty = build_ip_profile('198.51.100.30', now=now)
        self.assertEqual(empty['behavior']['risk']['total_requests'], 0)
        self.assertEqual(empty['behavior']['risk']['error_rate'], 0)
        self.assertEqual(empty['behavior']['risk']['anomaly_level'], 'normal')

    def test_whitelist_keeps_anomaly_details_but_overrides_security_risk(self):
        now = timezone.now()
        self._create_spread_logs('198.51.100.31', 68, 66, now, failed_status=400)
        rule = IpSecurityRule.objects.create(target='198.51.100.31', rule_type='whitelist')

        whitelisted = build_ip_profile('198.51.100.31', now=now)
        self.assertEqual(whitelisted['risk_level'], 'low')
        self.assertEqual(whitelisted['risk_score'], 0)
        self.assertEqual(whitelisted['behavior']['risk']['anomaly_level'], 'high')

        rule.status = 'revoked'
        rule.save(update_fields=['status'])
        restored = build_ip_profile('198.51.100.31', now=now)
        self.assertEqual(restored['risk_level'], 'high')
        self.assertGreaterEqual(restored['risk_score'], 50)


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

    def _set_created_at(self, rows, created_at):
        AccessLog.objects.filter(pk__in=[row.pk for row in rows]).update(created_at=created_at)

    def test_overview_is_independent_from_profile_filters_and_uses_recent_window(self):
        AccessLog.objects.all().delete()
        now = timezone.now()
        active = []
        for ip, code in (
            ('198.51.100.40', 200),
            ('198.51.100.41', 400),
            ('198.51.100.42', 500),
        ):
            row = AccessLog.objects.create(
                ip_address=ip,
                method='GET',
                path='/api/health/',
                status_code=code,
            )
            active.append(row)
        auth_failures = [
            AccessLog.objects.create(
                ip_address='198.51.100.42',
                method='POST',
                path='/api/auth/login/',
                status_code=401,
            )
            for _ in range(8)
        ]
        old = AccessLog.objects.create(
            ip_address='198.51.100.99',
            method='GET',
            path='/api/old/',
            status_code=500,
        )
        self._set_created_at(active + auth_failures, now - timedelta(hours=1))
        self._set_created_at([old], now - timedelta(days=8))
        IpSecurityRule.objects.create(target='198.51.100.41', rule_type='whitelist')
        AccessLog.objects.filter(pk=active[2].pk).update(security_action='blocked')
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/access-logs/overview/', {
            'ip': '198.51.100.40',
            'risk': 'low',
            'network': 'private',
            'region': '不存在',
            'page': 9,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['data']['active_ips'],
            3,
        )
        self.assertEqual(response.data['data']['high_risk_ips'], 1)
        self.assertEqual(response.data['data']['active_rules'], 1)
        self.assertEqual(response.data['data']['blocked_requests'], 1)
        self.assertIn('window_start', response.data['data'])
        self.assertIn('window_end', response.data['data'])

    def test_overview_counts_each_ip_once_even_with_default_model_ordering(self):
        AccessLog.objects.all().delete()
        now = timezone.now()
        first = AccessLog.objects.create(
            ip_address='198.51.100.60',
            method='GET',
            path='/api/health/',
            status_code=200,
        )
        second = AccessLog.objects.create(
            ip_address='198.51.100.60',
            method='GET',
            path='/api/health/',
            status_code=200,
        )
        self._set_created_at([first], now - timedelta(hours=1))
        self._set_created_at([second], now - timedelta(hours=2))
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/access-logs/overview/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['active_ips'], 1)
        self.assertEqual(response.data['data']['high_risk_ips'], 0)

    def test_profiles_window_and_blocked_group_filter_are_explicit(self):
        AccessLog.objects.all().delete()
        now = timezone.now()
        recent = AccessLog.objects.create(
            ip_address='198.51.100.50',
            method='GET',
            path='/api/recent/',
            status_code=403,
            security_action='blocked',
        )
        old = AccessLog.objects.create(
            ip_address='198.51.100.51',
            method='GET',
            path='/api/old/',
            status_code=403,
            security_action='blocked',
        )
        self._set_created_at([recent], now - timedelta(hours=1))
        self._set_created_at([old], now - timedelta(days=8))
        self.client.force_authenticate(self.user)

        profiles = self.client.get('/api/access-logs/profiles/', {'window': '7d'})
        self.assertEqual(profiles.status_code, status.HTTP_200_OK)
        self.assertEqual(profiles.data['data']['total'], 1)
        self.assertEqual(profiles.data['data']['list'][0]['ip_address'], '198.51.100.50')

        blocked = self.client.get('/api/access-logs/', {'securityGroup': 'blocked', 'window': '7d'})
        self.assertEqual(blocked.status_code, status.HTTP_200_OK)
        self.assertEqual(blocked.data['data']['total'], 1)
        self.assertEqual(blocked.data['data']['list'][0]['security_action'], 'blocked')

    def test_invalid_profile_window_and_security_group_return_bad_request(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.get('/api/access-logs/profiles/', {'window': '30d'}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.get('/api/access-logs/', {'securityGroup': 'unknown'}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

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
