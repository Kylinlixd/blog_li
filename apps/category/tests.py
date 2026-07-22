from rest_framework import status
from rest_framework.test import APITestCase

from apps.category.models import Category


class CategoryPermissionTests(APITestCase):
    def setUp(self):
        Category.objects.create(name='工程实践')

    def test_admin_category_list_requires_authentication(self):
        response = self.client.get('/api/categories/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_category_list_remains_available(self):
        response = self.client.get('/blog/categories/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'][0]['name'], '工程实践')
