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

    def test_login_returns_access_and_sets_http_only_refresh_cookie(self):
        response = self.client.post('/api/auth/login/', {
            'username': self.user.username,
            'password': 'correct-horse-battery-staple',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data'])
        self.assertNotIn('refresh', response.data['data'])
        cookie = response.cookies['refresh_token']
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')

    def test_refresh_uses_the_http_only_cookie_without_returning_a_refresh_token(self):
        login_response = self.client.post('/api/auth/login/', {
            'username': self.user.username,
            'password': 'correct-horse-battery-staple',
        })

        response = self.client.post('/api/token/refresh/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data'])
        self.assertNotIn('refresh', response.data['data'])
        self.assertNotEqual(response.data['data']['access'], login_response.data['data']['access'])

    def test_login_accepts_email_after_username_change(self):
        self.user.email = 'editor@example.com'
        self.user.save(update_fields=['email'])
        response = self.client.post('/api/auth/login/', {
            'username': ' EDITOR@EXAMPLE.COM ',
            'password': 'correct-horse-battery-staple'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data['data'])

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

    def test_authenticated_user_can_update_profile(self):
        self.client.force_authenticate(self.user)

        response = self.client.put('/api/auth/profile/', {
            'username': 'editor-renamed',
            'nickname': '编辑后的昵称',
            'email': 'updated@example.com',
            'bio': '新的个人简介',
            'avatar': 'https://example.com/avatar.png',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'editor-renamed')
        self.assertEqual(self.user.nickname, '编辑后的昵称')
        self.assertEqual(response.data['data']['email'], 'updated@example.com')

    def test_authenticated_user_can_change_password(self):
        self.client.force_authenticate(self.user)

        response = self.client.put('/api/auth/password/', {
            'old_password': 'correct-horse-battery-staple',
            'new_password': 'New-safe-password-123',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('New-safe-password-123'))

    def test_regular_user_cannot_enumerate_user_management_resources(self):
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/users/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
