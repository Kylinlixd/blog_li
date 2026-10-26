from datetime import datetime as dt
from datetime import timezone as dt_timezone

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.dynamic.models import Dynamic

from .models import Collection, CollectionItem


class CollectionAdminApiTests(APITestCase):
    def setUp(self):
        self.editor = get_user_model().objects.create_user(
            username='collection-editor',
            email='collection-editor@example.com',
            password='x',
            role='editor',
        )
        self.collection = Collection.objects.create(
            title='Java 技术文章合集', description='后端进阶', series='Java与Spring'
        )
        self.published = Dynamic.objects.create(
            author=self.editor, title='已发布文章', content='内容', status='published'
        )
        self.draft = Dynamic.objects.create(
            author=self.editor, title='草稿文章', content='内容', status='draft'
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.editor)

    def test_admin_endpoints_require_content_editor(self):
        response = self.client.get('/api/collections/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        response = self.client.get('/api/collections/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_and_update_collection(self):
        self.authenticate()
        response = self.client.post('/api/collections/', {
            'title': '存储与缓存合集',
            'description': 'Redis 与 MySQL',
            'series': '存储与缓存',
            'status': 'active',
            'sort': 3,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        collection_id = response.data['data']['id']

        response = self.client.patch(f'/api/collections/{collection_id}/', {
            'description': '更新后的简介',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Collection.objects.get(pk=collection_id).description, '更新后的简介'
        )

    def test_item_count_separates_drafts_from_published(self):
        CollectionItem.objects.create(collection=self.collection, dynamic=self.published, sort=1)
        CollectionItem.objects.create(collection=self.collection, dynamic=self.draft, sort=2)

        self.authenticate()
        response = self.client.get('/api/collections/')
        item = response.data['data']['items'][0]
        self.assertEqual(item['itemCount'], 2)
        self.assertEqual(item['publishedCount'], 1)

        public = self.client.get(f'/api/blog/collections/{self.collection.id}/')
        self.assertEqual(public.data['data']['itemCount'], 1)
        self.assertEqual([entry['id'] for entry in public.data['data']['items']], [self.published.id])

    def test_replace_items_persists_order_and_rejects_duplicates(self):
        self.authenticate()
        response = self.client.put(f'/api/collections/{self.collection.id}/items/', {
            'items': [
                {'dynamicId': self.draft.id},
                {'dynamicId': self.published.id},
            ],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([entry['id'] for entry in response.data['data']], [self.draft.id, self.published.id])
        self.assertEqual(
            list(CollectionItem.objects.filter(collection=self.collection).order_by('sort').values_list('sort', flat=True)),
            [1, 2],
        )

        response = self.client.put(f'/api/collections/{self.collection.id}/items/', {
            'items': [
                {'dynamicId': self.published.id},
                {'dynamicId': self.published.id},
            ],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_destroy_hides_collection_with_items_and_deletes_empty_one(self):
        CollectionItem.objects.create(collection=self.collection, dynamic=self.published, sort=1)
        self.authenticate()

        response = self.client.delete(f'/api/collections/{self.collection.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, 'hidden')

        empty = Collection.objects.create(title='空合集')
        response = self.client.delete(f'/api/collections/{empty.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Collection.objects.filter(pk=empty.id).exists())

    def test_article_save_syncs_collection_membership(self):
        self.authenticate()
        response = self.client.post('/api/dynamics/', {
            'title': '带合集的文章',
            'content': '正文',
            'status': 'published',
            'collectionIds': [self.collection.id],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dynamic_id = response.data['data']['id']
        self.assertTrue(
            CollectionItem.objects.filter(collection=self.collection, dynamic_id=dynamic_id).exists()
        )

        detail = self.client.get(f'/api/dynamics/{dynamic_id}/')
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['data']['collections'][0]['id'], self.collection.id)

        response = self.client.put(f'/api/dynamics/{dynamic_id}/', {
            'title': '带合集的文章',
            'content': '正文',
            'status': 'published',
            'collectionIds': [],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            CollectionItem.objects.filter(collection=self.collection, dynamic_id=dynamic_id).exists()
        )

    def test_item_without_collection_id_is_ignored(self):
        self.authenticate()
        response = self.client.post('/api/dynamics/', {
            'title': '普通文章',
            'content': '正文',
            'status': 'published',
            'collectionIds': [999999],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dynamic_id = response.data['data']['id']
        self.assertFalse(CollectionItem.objects.filter(dynamic_id=dynamic_id).exists())

    def test_options_only_lists_active_collections(self):
        Collection.objects.create(title='隐藏合集', status='hidden')
        self.authenticate()
        response = self.client.get('/api/collections/options/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([entry['title'] for entry in response.data['data']], ['Java 技术文章合集'])


class BlogCollectionPublicApiTests(APITestCase):
    """前台合集目录：默认从最早看起，order=latest 按发布时间倒序。"""

    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username='blog-reader-author',
            email='blog-reader-author@example.com',
            password='x',
        )
        self.collection = Collection.objects.create(
            title='读书笔记专栏', description='每周一篇', series='读书笔记', status='active'
        )
        self.fixtures = [
            # (sort, 标题, 发布时间) 刻意让目录顺序与时间顺序不同，证明排序真实生效
            (1, '最早发布', dt(2026, 8, 2, 20, 30, tzinfo=dt_timezone.utc)),
            (2, '最新发布', dt(2026, 10, 4, 20, 30, tzinfo=dt_timezone.utc)),
            (3, '中间发布', dt(2026, 9, 6, 20, 30, tzinfo=dt_timezone.utc)),
        ]
        for sort, title, created_at in self.fixtures:
            dynamic = Dynamic.objects.create(
                author=self.author, title=title, content='正文', status='published'
            )
            Dynamic.objects.filter(pk=dynamic.pk).update(created_at=created_at)
            CollectionItem.objects.create(
                collection=self.collection, dynamic=dynamic, sort=sort
            )
        self.draft = Dynamic.objects.create(
            author=self.author, title='未发布草稿', content='内容', status='draft'
        )
        CollectionItem.objects.create(
            collection=self.collection, dynamic=self.draft, sort=4
        )

    def fetch_titles(self, query=''):
        response = self.client.get(f'/api/blog/collections/{self.collection.pk}/{query}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        return [item['title'] for item in response.data['data']['items']]

    def test_default_returns_collection_order_without_drafts(self):
        self.assertEqual(self.fetch_titles(), ['最早发布', '最新发布', '中间发布'])

    def test_order_latest_returns_publish_time_desc(self):
        self.assertEqual(self.fetch_titles('?order=latest'), ['最新发布', '中间发布', '最早发布'])

    def test_order_latest_is_case_insensitive(self):
        self.assertEqual(self.fetch_titles('?order=LATEST'), ['最新发布', '中间发布', '最早发布'])

    def test_unknown_order_falls_back_to_collection_order(self):
        self.assertEqual(self.fetch_titles('?order=bogus'), ['最早发布', '最新发布', '中间发布'])
