"""第一批审计修复的回归测试。

覆盖：
1. 公开接口的参数错误返回 4xx 而不是 5xx（分页越界、pageSize 非整数）；
2. 查询数不随返回行数增长（序列化器不再逐行补充查询）。
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from apps.category.models import Category
from apps.comment.models import Comment
from apps.dynamic.models import Dynamic
from apps.tag.models import Tag
from apps.upload.models import UploadFile


class PublicEndpointParameterTests(APITestCase):
    """参数写错不该变成 500：客户端错误应返回 4xx。"""

    def setUp(self):
        user = get_user_model().objects.create_user(
            username='editor', email='editor@example.com', password='x', role='editor'
        )
        self.category = Category.objects.create(name='工程实践')
        self.tag = Tag.objects.create(name='Vue')
        self.published = Dynamic.objects.create(
            author=user,
            category=self.category,
            title='Vue 请求层重构',
            content='统一认证与错误处理',
            status='published',
        )
        self.published.tags.add(self.tag)

    def test_search_rejects_out_of_range_page_size(self):
        response = self.client.get('/api/blog/search/?keyword=Vue&pageSize=999')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertLess(response.status_code, 500)

    def test_search_rejects_non_integer_page_size(self):
        response = self.client.get('/api/blog/search/?keyword=Vue&pageSize=abc')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_category_dynamics_rejects_out_of_range_page(self):
        response = self.client.get(f'/api/blog/categories/{self.category.pk}/dynamics/?page=999')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tag_dynamics_rejects_out_of_range_page(self):
        response = self.client.get(f'/api/blog/tags/{self.tag.pk}/dynamics/?page=999')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_threaded_comments_reject_non_integer_page_size(self):
        Comment.objects.create(
            dynamic=self.published,
            author=self.published.author,
            content='第一条',
            status='approved',
        )

        response = self.client.get(
            f'/api/blog/comments/?dynamic_id={self.published.pk}&thread=1&pageSize=abc'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unexpected_error_still_returns_500(self):
        """只有 DRF 异常放行；真正的内部错误仍应是 500（保持既有的不泄露原则）。"""
        from unittest.mock import patch

        with patch('apps.dynamic.views.Category.objects.get', side_effect=RuntimeError('boom')):
            response = self.client.get(f'/api/blog/categories/{self.category.pk}/dynamics/')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertNotIn('boom', str(response.data))


class PublicListQueryCountTests(APITestCase):
    """列表查询数不应随返回行数线性增长（逐行 COUNT / 逐行重查文件）。"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='editor2', email='editor2@example.com', password='x', role='editor'
        )
        self.category = Category.objects.create(name='前端')

    def _create_dynamic(self, title, with_file):
        dynamic = Dynamic.objects.create(
            author=self.user,
            category=self.category,
            title=title,
            content='内容',
            status='published',
        )
        if with_file:
            upload = UploadFile.objects.create(
                name=f'{title}.png',
                file_type='image',
                file_size=10,
                file_url=f'/api/upload/private/{title}/',
                storage_backend='local',
                storage_key=f'image/{title}.png',
                checksum='abc',
                content_type='image/png',
                uploader=self.user,
                is_public=True,
            )
            dynamic.files.add(upload)
        return dynamic

    def _list_queries(self, page_size):
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(f'/api/blog/dynamics/?page_size={page_size}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return len(captured)

    def test_query_count_does_not_grow_with_row_count(self):
        self._create_dynamic('only-one', with_file=True)
        single = self._list_queries(1)

        for index in range(4):
            self._create_dynamic(f'row-{index}', with_file=True)
        many = self._list_queries(10)

        # 5 行的查询数与 1 行基本一致；旧实现是每行多 4 次查询，会相差十几条
        self.assertLessEqual(
            many,
            single + 3,
            f'查询数随行数增长：1 行 {single} 条，5 行 {many} 条',
        )


class MiddlewareLoggingTests(SimpleTestCase):
    """经中间件转成 500 的异常必须留下日志，否则线上无从排查。"""

    def test_unhandled_exception_is_logged_with_request_id(self):
        from blog.middleware import APIExceptionMiddleware

        middleware = APIExceptionMiddleware(lambda request: None)
        request = APIRequestFactory().get('/api/blog/dynamics/')
        request.request_id = 'test-request-id'

        with self.assertLogs('blog.middleware', level='ERROR') as captured:
            response = middleware.process_exception(request, RuntimeError('storage exploded'))

        self.assertEqual(response.status_code, 500)
        joined = '\n'.join(captured.output)
        self.assertIn('未处理异常', joined)
        self.assertIn('test-request-id', joined)
        self.assertIn('storage exploded', joined)

    def test_integrity_error_is_logged_as_warning(self):
        from django.db import IntegrityError

        from blog.middleware import APIExceptionMiddleware

        middleware = APIExceptionMiddleware(lambda request: None)
        request = APIRequestFactory().post('/api/comments/')
        request.request_id = 'req-2'

        with self.assertLogs('blog.middleware', level='WARNING') as captured:
            response = middleware.process_exception(request, IntegrityError('duplicate'))

        self.assertEqual(response.status_code, 400)
        self.assertIn('数据完整性错误', '\n'.join(captured.output))


class StandardPaginationTests(APITestCase):
    """管理端列表的「每页条数」必须真的生效。

    这些 viewset 之前没配 pagination_class，落到 DRF 全局默认（固定 10、不接受 pageSize），
    前端切到 20/50/100 时每页仍然只有 10 条，页码与总数会对不上。
    """

    def setUp(self):
        from apps.category.models import Category as CategoryModel
        from apps.tag.models import Tag as TagModel

        self.user = get_user_model().objects.create_user(
            username='editor-pagination', email='pagination@example.com', password='x', role='editor'
        )
        for index in range(12):
            CategoryModel.objects.create(name=f'分类-{index:02d}')
            TagModel.objects.create(name=f'标签-{index:02d}')
        self.client.force_authenticate(self.user)

    def test_category_list_honours_page_size(self):
        response = self.client.get('/api/categories/?pageSize=20')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 10)

    def test_tag_list_honours_page_size(self):
        response = self.client.get('/api/tags/?pageSize=20')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 10)

    def test_page_size_is_capped(self):
        response = self.client.get('/api/tags/?pageSize=100000')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data['results']), 100)


class PublicWriteThrottleTests(APITestCase):
    """公开点赞接口必须限速，且限速要能真的触发 429。"""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.user = get_user_model().objects.create_user(
            username='editor-throttle', email='throttle@example.com', password='x', role='editor'
        )
        self.published = Dynamic.objects.create(
            author=self.user, title='限流测试', content='内容', status='published'
        )

    def test_like_is_throttled(self):
        # SimpleRateThrottle.THROTTLE_RATES 在类定义时就固化了，
        # override_settings 改不动它，必须直接替换类属性（DRF 自己的测试也是这么做的）。
        from unittest.mock import patch

        from rest_framework.throttling import ScopedRateThrottle

        with patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'public_like': '3/minute'}):
            statuses = [
                self.client.post(f'/api/blog/dynamics/{self.published.pk}/like/').status_code
                for _ in range(5)
            ]

        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses)

    def test_view_endpoint_is_throttled_with_its_own_scope(self):
        from unittest.mock import patch

        from rest_framework.throttling import ScopedRateThrottle

        with patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'public_view': '2/minute'}):
            statuses = [
                self.client.put(f'/api/blog/dynamics/{self.published.pk}/view/').status_code
                for _ in range(5)
            ]

        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses)


class AudioValidationTests(SimpleTestCase):
    """音频不再跳过内容校验：扩展名/MIME/魔数都要对得上。"""

    def _upload(self, name, content, content_type):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_valid_mp3_is_accepted(self):
        from apps.upload.validation import validate_file_type

        ok, error = validate_file_type(self._upload('a.mp3', b'ID3\x03\x00\x00\x00', 'audio/mpeg'), 'audio')

        self.assertTrue(ok, error)

    def test_disguised_script_is_rejected(self):
        from apps.upload.validation import validate_file_type

        ok, error = validate_file_type(self._upload('a.mp3', b'<?php echo 1; ?>', 'audio/mpeg'), 'audio')

        self.assertFalse(ok)
        self.assertIn('不符', error or '')

    def test_unknown_audio_extension_is_rejected(self):
        from apps.upload.validation import validate_file_type

        ok, _error = validate_file_type(self._upload('a.exe', b'MZ\x90\x00', 'audio/mpeg'), 'audio')

        self.assertFalse(ok)
