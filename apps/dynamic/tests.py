from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.category.models import Category
from apps.dynamic.models import Dynamic
from apps.tag.models import Tag


class DynamicAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='editor',
            email='editor@example.com',
            password='correct-horse-battery-staple',
        )
        self.category = Category.objects.create(name='工程实践')
        self.tag = Tag.objects.create(name='Vue')
        self.published = Dynamic.objects.create(
            author=self.user,
            category=self.category,
            title='Vue 请求层重构',
            content='统一认证与错误处理',
            status='published',
        )
        self.published.tags.add(self.tag)
        Dynamic.objects.create(
            author=self.user,
            category=self.category,
            title='尚未公开',
            content='草稿内容',
            status='draft',
        )

    def test_public_list_only_returns_published_content(self):
        response = self.client.get('/blog/dynamics/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 1)
        self.assertEqual(response.data['data']['items'][0]['title'], self.published.title)

    def test_admin_list_requires_authentication(self):
        response = self.client.get('/api/dynamics/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_search_matches_title(self):
        response = self.client.get('/blog/dynamics/', {'keyword': '请求层'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 1)

    def test_detail_includes_category_and_tags(self):
        response = self.client.get(f'/blog/dynamics/{self.published.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['category']['name'], self.category.name)
        self.assertEqual(response.data['data']['tags'][0]['name'], self.tag.name)

    def test_view_action_increments_count(self):
        response = self.client.put(f'/blog/dynamics/{self.published.pk}/view/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.published.refresh_from_db()
        self.assertEqual(self.published.view_count, 1)

    def test_hot_endpoint_rejects_invalid_limit(self):
        response = self.client.get('/blog/dynamics/hot/', {'limit': 'many'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
