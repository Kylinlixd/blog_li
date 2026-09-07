import io
from datetime import timedelta
from unittest.mock import patch, Mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import AccessLog, IpGeoRecord, IpSecurityRule
from .profile import build_ip_profile, lookup_geo


class GeoTests(TestCase):
    @patch('requests.post')
    def test_360_unicode_isp_and_persistent_cache(self, post):
        response = Mock()
        response.json.return_value = {'errno': 0, 'data': '\u6d59\u6c5f\u7701\u676d\u5dde\u5e02\t\u7535\u4fe1'}
        post.return_value = response
        geo = lookup_geo('36.28.161.127')
        self.assertEqual(geo['region'], '浙江省')
        self.assertEqual(geo['city'], '杭州市')
        self.assertEqual(geo['isp'], '电信')
        self.assertTrue(geo['matched'])
        self.assertEqual(lookup_geo('36.28.161.127'), geo)
        self.assertEqual(post.call_count, 1)

    @patch('requests.post')
    def test_private_address_never_sent_to_provider(self, post):
        self.assertEqual(lookup_geo('192.168.1.1')['region'], '内网')
        post.assert_not_called()

    @patch('requests.post')
    def test_provider_failure_keeps_offline_fallback(self, post):
        import requests
        post.side_effect = requests.Timeout()
        IpGeoRecord.objects.create(network='36.28.0.0/16', region='浙江省', city='杭州市')
        self.assertEqual(lookup_geo('36.28.161.127')['city'], '杭州市')
        self.assertFalse(lookup_geo('8.8.8.8')['matched'])

    @patch('requests.post')
    def test_refresh_deduplicates_historical_ips(self, post):
        post.return_value.json.return_value = {'errno': 0, 'data': '浙江省杭州市\t电信'}
        for ip in ['36.28.161.127', '36.28.161.127', '192.168.1.1']:
            AccessLog.objects.create(ip_address=ip, method='GET', path='/api/blog/dynamics/1/', status_code=200)
        output = io.StringIO()
        call_command('refresh_ip_geo', all=True, delay=0, stdout=output)
        self.assertEqual(post.call_count, 1)
        self.assertIn('成功 1', output.getvalue())


class ProfileFilterTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='filters', is_staff=True)
        self.client.force_authenticate(self.user)
        for ip, n in [('192.168.1.1', 1), ('198.51.100.2', 8), ('198.51.100.3', 70)]:
            AccessLog.objects.bulk_create([AccessLog(ip_address=ip, method='POST', path='/api/auth/login/', status_code=401) for _ in range(n)])

    def test_exact_risk_filter_applies_before_pagination(self):
        result = self.client.get('/api/access-logs/profiles/', {'risk': 'high', 'pageSize': 1}).data['data']
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['list'][0]['ip_address'], '198.51.100.2')
        critical = self.client.get('/api/access-logs/profiles/', {'risk': 'critical'}).data['data']
        self.assertEqual(critical['total'], 1)
        low = self.client.get('/api/access-logs/profiles/', {'risk': 'low'}).data['data']
        self.assertEqual(low['total'], 1)

    def test_whitelist_cidr_overrides_risk_until_expiry(self):
        rule = IpSecurityRule.objects.create(target='198.51.100.0/24', rule_type='whitelist')
        self.assertEqual(build_ip_profile('198.51.100.3')['risk_level'], 'low')
        result = self.client.get('/api/access-logs/profiles/', {'risk': 'critical'}).data['data']
        self.assertEqual(result['total'], 0)
        rule.expires_at = timezone.now() - timedelta(seconds=1)
        rule.save()
        self.assertEqual(build_ip_profile('198.51.100.3')['risk_level'], 'critical')

    def test_network_region_and_cidr_filters(self):
        IpGeoRecord.objects.create(network='198.51.100.0/24', region='浙江省', city='杭州市')
        result = self.client.get('/api/access-logs/profiles/', {'region': '杭州', 'ip': '198.51.100.0/24'}).data['data']
        self.assertEqual(result['total'], 2)
        result = self.client.get('/api/access-logs/profiles/', {'network': 'public'}).data['data']
        self.assertEqual(result['total'], 0)
        result = self.client.get('/api/access-logs/profiles/', {'network': 'private', 'ip': '192.168'}).data['data']
        self.assertEqual(result['total'], 1)

    def test_profile_collection_query_count_does_not_grow_per_ip(self):
        from .profile import build_ip_profiles
        with self.assertNumQueries(5):
            profiles = build_ip_profiles(['192.168.1.1', '198.51.100.2', '198.51.100.3'])
        self.assertEqual(len(profiles), 3)
        self.assertEqual(profiles[2]['risk_level'], 'critical')


class GeoFailureTests(TestCase):
    @patch('requests.post')
    def test_failed_refresh_preserves_success_and_can_be_retried(self, post):
        from .models import IpGeoCache
        from .geo import URL
        post.return_value.json.return_value = {'errno': 0, 'data': '浙江省杭州市\t电信'}
        known = lookup_geo('36.28.161.127')
        self.assertEqual(post.call_args.args, (URL,))
        self.assertEqual(post.call_args.kwargs['headers']['Referer'], 'http://ip.360.cn/')
        post.return_value.json.return_value = {'errno': 1, 'data': ''}
        self.assertEqual(lookup_geo('36.28.161.127', force=True), known)
        cached = IpGeoCache.objects.get(ip_address='36.28.161.127')
        self.assertFalse(cached.lookup_ok)
        self.assertEqual(cached.data['city'], '杭州市')

    def test_location_parser_preserves_foreign_and_municipal_locations(self):
        from .geo import parse_location
        self.assertEqual(parse_location('北京市\t联通')['region'], '北京市')
        self.assertEqual(parse_location('美国加利福尼亚州\t云服务商')['location'], '美国加利福尼亚州')
        self.assertIsNone(parse_location(None))
        self.assertIsNone(parse_location('未知'))
