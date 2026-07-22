from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class AuthTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='editor',
            email='editor@example.com',
            password='correct-horse-battery-staple',
        )

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post('/api/auth/login/', {
            'username': self.user.username,
            'password': 'correct-horse-battery-staple',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])

    def test_user_info_requires_authentication(self):
        response = self.client.get('/api/auth/info/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
