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

    def test_user_info_accepts_login_access_token(self):
        login_response = self.client.post('/api/auth/login/', {
            'username': self.user.username,
            'password': 'correct-horse-battery-staple',
        })
        access = login_response.data['data']['access']

        response = self.client.get(
            '/api/auth/info/',
            HTTP_AUTHORIZATION=f'Bearer {access}',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['username'], self.user.username)

    def test_anonymous_registration_is_denied(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'visitor',
            'email': 'visitor@example.com',
            'password': 'safe-password-123',
            'confirm_password': 'safe-password-123',
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_an_account(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_authenticate(self.user)

        response = self.client.post('/api/auth/register/', {
            'username': 'writer',
            'email': 'writer@example.com',
            'password': 'safe-password-123',
            'confirm_password': 'safe-password-123',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(get_user_model().objects.filter(username='writer').exists())
