from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from apps.comment.models import Comment
from apps.dynamic.models import Dynamic


class PublicCommentVisibilityTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username='comment-author')
        self.dynamic = Dynamic.objects.create(
            author=self.user,
            title='公开文章',
            content='正文',
            status='published',
        )
        Comment.objects.create(
            author=self.user,
            dynamic=self.dynamic,
            content='公开评论',
            status='approved',
        )
        Comment.objects.create(
            author=self.user,
            dynamic=self.dynamic,
            content='等待审核',
            status='pending',
        )

    def test_public_list_only_returns_approved_comments(self):
        response = self.client.get('/api/blog/comments/', {'dynamic_id': self.dynamic.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 1)
        self.assertEqual(response.data['data']['list'][0]['content'], '公开评论')
        self.assertNotIn('email', response.data['data']['list'][0])

    def test_thread_mode_returns_replies_without_exposing_email(self):
        root = Comment.objects.create(
            author=self.user,
            dynamic=self.dynamic,
            content='根评论',
            nickname='夕月',
            status='approved',
        )
        Comment.objects.create(
            author=self.user,
            dynamic=self.dynamic,
            parent=root,
            content='回复评论',
            nickname='小东',
            status='approved',
        )

        response = self.client.get('/api/blog/comments/', {
            'dynamic_id': self.dynamic.pk,
            'thread': '1',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = next(row for row in response.data['data']['list'] if row['content'] == '根评论')
        self.assertEqual(item['reply_count'], 1)
        self.assertEqual(item['replies_preview'][0]['reply_to_nickname'], '夕月')
        self.assertNotIn('email', item['replies_preview'][0])

    def test_public_reply_rejects_parent_from_another_dynamic(self):
        other = Dynamic.objects.create(
            author=self.user,
            title='另一篇文章',
            content='正文',
            status='published',
        )
        parent = Comment.objects.create(
            author=self.user,
            dynamic=other,
            content='其他文章评论',
            status='approved',
        )
        response = self.client.post('/api/blog/comments/', {
            'dynamic_id': self.dynamic.pk,
            'parent_id': parent.pk,
            'content': '跨文章回复',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Comment.objects.filter(content='跨文章回复').exists())

    def test_public_list_does_not_expose_comments_from_a_draft(self):
        draft = Dynamic.objects.create(
            author=self.user,
            title='尚未公开的文章',
            content='草稿正文',
            status='draft',
        )
        Comment.objects.create(
            author=self.user,
            dynamic=draft,
            content='不应展示',
            status='approved',
        )

        response = self.client.get('/api/blog/comments/', {'dynamic_id': draft.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 0)

    def test_public_comment_uses_a_dedicated_guest_account(self):
        response = self.client.post('/api/blog/comments/', {
            'dynamic_id': self.dynamic.pk,
            'content': '来自访客的反馈',
            'nickname': '访客',
            'email': 'visitor@example.com',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment = Comment.objects.get(content='来自访客的反馈')
        self.assertEqual(comment.author.username, 'guest')
        self.assertNotEqual(comment.author_id, self.user.pk)

    def test_api_blog_prefix_allows_anonymous_comment_submission(self):
        response = self.client.post('/api/blog/comments/', {
            'dynamic_id': self.dynamic.pk,
            'content': '来自移动端的反馈',
            'nickname': '移动访客',
            'email': 'mobile@example.com',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Comment.objects.filter(content='来自移动端的反馈').exists())

    def test_clean_comment_is_approved_automatically(self):
        response = self.client.post('/api/blog/comments/', {
            'dynamic_id': self.dynamic.pk,
            'content': '这篇文章很有帮助，谢谢分享',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'approved')

    def test_abusive_comment_waits_for_manual_review(self):
        response = self.client.post('/api/blog/comments/', {
            'dynamic_id': self.dynamic.pk,
            'content': '你这个垃圾作者',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'pending')

    def test_violent_or_explicit_comment_is_rejected_with_guidance(self):
        response = self.client.post('/api/blog/comments/', {
            'dynamic_id': self.dynamic.pk,
            'content': '这里包含色情内容',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('请规范言辞', response.data['message'])

    def test_profanity_variants_are_rejected(self):
        for content in ('操你妈', '操 你 妈', '操-你-妈'):
            response = self.client.post('/api/blog/comments/', {
                'dynamic_id': self.dynamic.pk,
                'content': content,
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('请规范言辞', response.data['message'])

    def test_public_comment_rejects_unpublished_content(self):
        draft = Dynamic.objects.create(
            author=self.user,
            title='草稿',
            content='尚未公开',
            status='draft',
        )

        response = self.client.post('/api/blog/comments/', {
            'dynamic_id': draft.pk,
            'content': '不应写入',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Comment.objects.filter(content='不应写入').exists())

    def test_public_comment_submission_is_rate_limited(self):
        payload = {
            'dynamic_id': self.dynamic.pk,
            'content': '限流测试评论',
        }
        for _ in range(10):
            response = self.client.post('/api/blog/comments/', payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post('/api/blog/comments/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
