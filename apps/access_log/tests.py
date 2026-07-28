from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from .models import AccessLog
from .device import parse_user_agent
from django.core.management import call_command
from datetime import timedelta
from django.utils import timezone
from django.utils import timezone


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
