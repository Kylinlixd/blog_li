from django.test import TestCase
from apps.user.models import User
# Create your tests here.
from rest_framework.test import APITestCase

class AuthTests(APITestCase):
    def test_login(self):
        user = User.objects.create_user(username='test', password='123456')
        response = self.client.post('/api/auth/login', {
            'username': 'test',
            'password': '123456'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data['data'])