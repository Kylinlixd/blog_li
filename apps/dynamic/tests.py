from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.cache import cache

from apps.category.models import Category
from apps.dynamic.models import Dynamic
from apps.dynamic.serializers import AdminDynamicSerializer, SimpleDynamicSerializer
from apps.tag.models import Tag
from apps.upload.models import UploadFile


class DynamicAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username='editor',
            email='editor@example.com',
            password='correct-horse-battery-staple',
            role='editor',
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
        self.draft = Dynamic.objects.create(
            author=self.user,
            category=self.category,
            title='尚未公开',
            content='草稿内容',
            status='draft',
        )

    def test_public_list_only_returns_published_content(self):
        response = self.client.get('/api/blog/dynamics/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 1)
        self.assertEqual(response.data['data']['items'][0]['title'], self.published.title)

    def test_public_list_ignores_an_invalid_bearer_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer stale-admin-token')

        response = self.client.get('/api/blog/dynamics/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 1)

    def test_admin_list_requires_authentication(self):
        response = self.client.get('/api/dynamics/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_authenticated_user_cannot_open_admin_dynamic_list(self):
        regular = get_user_model().objects.create_user(
            username='reader',
            email='reader@example.com',
            password='safe-password-123',
        )
        self.client.force_authenticate(regular)

        response = self.client.get('/api/dynamics/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_search_matches_title(self):
        response = self.client.get('/api/blog/dynamics/', {'keyword': '请求层'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 1)

    def test_detail_includes_category_and_tags(self):
        response = self.client.get(f'/api/blog/dynamics/{self.published.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['category']['name'], self.category.name)
        self.assertEqual(response.data['data']['tags'][0]['name'], self.tag.name)

    def test_public_detail_returns_json_404_for_missing_or_unpublished_dynamic(self):
        for dynamic_id in (999999, self.draft.pk):
            response = self.client.get(f'/api/blog/dynamics/{dynamic_id}/')
            payload = response.data if hasattr(response, 'data') else response.json()

            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(payload['code'], 404)
            self.assertEqual(payload['message'], '文章不存在或已被删除')
            self.assertIsNone(payload['data'])

    def test_public_detail_does_not_expose_private_author_fields(self):
        response = self.client.get(f'/api/blog/dynamics/{self.published.pk}/')

        author = response.data['data']['author']
        self.assertNotIn('email', author)
        self.assertNotIn('role', author)
        self.assertNotIn('permissions', author)

    def test_detail_includes_content_type_and_media_urls(self):
        video = Dynamic.objects.create(
            author=self.user,
            category=self.category,
            title='视频记录',
            content='视频正文',
            type='video',
            status='published',
            media_urls=['/api/upload/public/48/'],
        )

        response = self.client.get(f'/api/blog/dynamics/{video.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['type'], 'video')
        self.assertEqual(response.data['data']['status'], 'published')
        self.assertEqual(response.data['data']['mediaUrls'], [{
            'url': '/api/upload/public/48/',
            'type': 'video',
        }])

    def test_detail_serializes_all_attached_media_as_objects(self):
        image = UploadFile.objects.create(
            name='cover.png', file_type='image', file_size=3,
            file_url='/api/upload/public/1/', uploader=self.user, is_public=True,
        )
        audio = UploadFile.objects.create(
            name='note.mp3', file_type='audio', file_size=5,
            file_url='/api/upload/public/2/', uploader=self.user, is_public=True,
        )
        self.published.files.add(image, audio)
        self.published.media_urls = ['/media/legacy.mp3']
        self.published.save(update_fields=['media_urls'])

        response = self.client.get(f'/api/blog/dynamics/{self.published.pk}/')

        media_by_url = {item['url']: item for item in response.data['data']['mediaUrls']}
        self.assertEqual(media_by_url[image.file_url], {
            'id': image.pk, 'url': image.file_url, 'type': 'image', 'name': image.name, 'size': image.file_size, 'poster_url': '',
        })
        self.assertEqual(media_by_url[audio.file_url], {
            'id': audio.pk, 'url': audio.file_url, 'type': 'audio', 'name': audio.name, 'size': audio.file_size, 'poster_url': '',
        })
        self.assertEqual(media_by_url['/media/legacy.mp3'], {'url': '/media/legacy.mp3', 'type': 'text'})

    def test_detail_orders_attached_media_by_file_id(self):
        image = UploadFile.objects.create(
            name='cover.png', file_type='image', file_size=3,
            file_url='/api/upload/public/1/', uploader=self.user, is_public=True,
        )
        audio = UploadFile.objects.create(
            name='note.mp3', file_type='audio', file_size=5,
            file_url='/api/upload/public/2/', uploader=self.user, is_public=True,
        )
        self.published.files.add(audio, image)

        response = self.client.get(f'/api/blog/dynamics/{self.published.pk}/')

        self.assertEqual(
            [item['id'] for item in response.data['data']['mediaUrls']],
            [image.pk, audio.pk],
        )

    def test_create_derives_type_from_the_first_attached_file(self):
        image = UploadFile.objects.create(
            name='cover.png', file_type='image', file_size=3,
            file_url='/api/upload/public/1/', uploader=self.user, is_public=True,
        )
        self.client.force_authenticate(self.user)

        response = self.client.post('/api/dynamics/', {
            'title': '自动类型',
            'content': '正文',
            'type': 'video',
            'status': 'draft',
            'mediaUrls': [image.file_url],
            'fileIds': [image.pk],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        created = Dynamic.objects.get(pk=response.data['data']['id'])
        self.assertEqual(created.type, 'image')

    def test_reading_detail_does_not_mutate_view_count(self):
        self.client.get(f'/api/blog/dynamics/{self.published.pk}/')

        self.published.refresh_from_db()
        self.assertEqual(self.published.view_count, 0)

    def test_view_action_increments_count(self):
        response = self.client.put(f'/api/blog/dynamics/{self.published.pk}/view/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.published.refresh_from_db()
        self.assertEqual(self.published.view_count, 1)

    def test_view_action_deduplicates_by_ip(self):
        for _ in range(2):
            self.client.put(f'/api/blog/dynamics/{self.published.pk}/view/')

        self.published.refresh_from_db()
        self.assertEqual(self.published.view_count, 1)

    def test_like_uses_forwarded_ip_for_deduplication(self):
        first = self.client.post(
            f'/api/blog/dynamics/{self.published.pk}/like/',
            HTTP_X_FORWARDED_FOR='203.0.113.5',
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        duplicate = self.client.post(
            f'/api/blog/dynamics/{self.published.pk}/like/',
            HTTP_X_FORWARDED_FOR='203.0.113.5',
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

        another_ip = self.client.post(
            f'/api/blog/dynamics/{self.published.pk}/like/',
            HTTP_X_FORWARDED_FOR='198.51.100.9',
        )
        self.assertEqual(another_ip.status_code, status.HTTP_200_OK)
        self.published.refresh_from_db()
        self.assertEqual(self.published.like_count, 2)

    def test_hot_endpoint_rejects_invalid_limit(self):
        response = self.client.get('/api/blog/dynamics/hot/', {'limit': 'many'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)

    def test_recent_endpoint_rejects_invalid_limit(self):
        response = self.client.get('/api/blog/dynamics/recent/', {'limit': 'many'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)

    def test_recent_endpoint_serializes_attached_cover_file(self):
        cover = UploadFile.objects.create(
            name='cover.png',
            file_type='image',
            file_size=123,
            file_url='/api/upload/public/1/',
            uploader=self.user,
            is_public=True,
        )
        self.published.files.add(cover)

        response = self.client.get('/api/blog/dynamics/recent/', {'limit': 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'][0]['files'][0]['name'], cover.name)
        self.assertEqual(response.data['data'][0]['files'][0]['file_url'], cover.file_url)

    def test_media_serializers_use_the_current_media_urls_field(self):
        image = Dynamic.objects.create(
            author=self.user,
            title='图片记录',
            content='图片正文',
            type='image',
            status='published',
            media_urls=['https://example.com/one.png', 'https://example.com/two.png'],
        )

        admin_data = AdminDynamicSerializer(image).data
        simple_data = SimpleDynamicSerializer(image).data

        self.assertEqual(admin_data['images'], image.media_urls)
        self.assertEqual(simple_data['mediaUrls'], image.media_urls)

    def test_update_preserves_category_tags_and_media(self):
        self.client.force_authenticate(self.user)
        second_category = Category.objects.create(name='后端实践')
        second_tag = Tag.objects.create(name='Django')

        response = self.client.put(f'/api/dynamics/{self.published.pk}/', {
            'title': '更新后的标题',
            'content': '更新后的正文',
            'type': 'image',
            'status': 'published',
            'categoryId': second_category.pk,
            'tags': [second_tag.pk],
            'mediaUrls': ['/media/cover.png'],
            'fileIds': [],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.published.refresh_from_db()
        self.assertEqual(self.published.category, second_category)
        self.assertEqual(
            list(self.published.tags.values_list('id', flat=True)),
            [second_tag.pk],
        )
        self.assertEqual(self.published.media_urls, ['/media/cover.png'])
        self.assertEqual(self.published.type, 'image')

    def test_update_with_only_file_ids_derives_type(self):
        image = UploadFile.objects.create(
            name='cover.png', file_type='image', file_size=3,
            file_url='/api/upload/public/1/', uploader=self.user, is_public=True,
        )
        self.client.force_authenticate(self.user)

        response = self.client.put(f'/api/dynamics/{self.published.pk}/', {
            'title': self.published.title,
            'content': self.published.content,
            'type': 'video',
            'status': self.published.status,
            'fileIds': [image.pk],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.published.refresh_from_db()
        self.assertEqual(self.published.type, 'image')
        self.assertEqual(list(self.published.files.values_list('id', flat=True)), [image.pk])

    @patch('apps.dynamic.views.Category.objects.get', side_effect=RuntimeError('database secret'))
    def test_category_errors_do_not_expose_internal_exception(self, _category_get):
        response = self.client.get('/api/blog/categories/1/dynamics/')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertNotIn('database secret', str(response.data))
