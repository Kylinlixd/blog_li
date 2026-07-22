from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class DashboardStatsTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='dashboard-editor',
            password='correct-horse-battery-staple',
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
