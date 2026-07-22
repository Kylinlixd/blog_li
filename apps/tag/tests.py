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
        response = self.client.get('/blog/tags/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
