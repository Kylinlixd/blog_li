from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from .models import AccessLog
from django.utils import timezone


class AccessLogTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='log-admin', password='safe-password-123', is_staff=True)

    def test_api_request_records_forwarded_ip(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/stats/', HTTP_X_FORWARDED_FOR='203.0.113.8, 10.0.0.1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(AccessLog.objects.filter(path='/api/stats/', ip_address='203.0.113.8', user=self.user).exists())

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

    def test_business_admin_role_can_read_logs_without_django_staff_flag(self):
        role_admin = get_user_model().objects.create_user(username='role-admin', email='role-admin@example.com', password='safe-password-123', role='admin')
        self.client.force_authenticate(role_admin)
        response = self.client.get('/api/access-logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_cannot_read_logs(self):
        regular = get_user_model().objects.create_user(username='regular-reader', email='regular-reader@example.com', password='safe-password-123', role='user')
        self.client.force_authenticate(regular)
        response = self.client.get('/api/access-logs/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
