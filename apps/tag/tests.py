from rest_framework import status
from rest_framework.test import APITestCase

from apps.tag.models import Tag


class TagPermissionTests(APITestCase):
    def setUp(self):
        Tag.objects.create(name='Vue')

    def test_admin_tag_list_requires_authentication(self):
        response = self.client.get('/api/tags/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_tag_list_remains_available(self):
        response = self.client.get('/api/blog/tags/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inactive_tags_are_hidden_from_public_list(self):
        Tag.objects.create(name='隐藏标签', status='inactive')

        response = self.client.get('/api/blog/tags/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['name'] for item in response.data['results']], ['Vue'])

    def test_regular_user_cannot_create_management_tag(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            username='reader',
            email='reader@example.com',
            password='safe-password-123',
        )
        self.client.force_authenticate(user)

        response = self.client.post('/api/tags/', {'name': '越权标签'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
