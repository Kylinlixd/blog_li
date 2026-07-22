from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.comment.models import Comment
from apps.dynamic.models import Dynamic


class PublicCommentVisibilityTests(APITestCase):
    def setUp(self):
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
        response = self.client.get('/blog/comments/', {'dynamic_id': self.dynamic.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 1)
        self.assertEqual(response.data['data']['list'][0]['content'], '公开评论')

    def test_public_comment_uses_a_dedicated_guest_account(self):
        response = self.client.post('/blog/comments/', {
            'dynamic_id': self.dynamic.pk,
            'content': '来自访客的反馈',
            'nickname': '访客',
            'email': 'visitor@example.com',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment = Comment.objects.get(content='来自访客的反馈')
        self.assertEqual(comment.author.username, 'guest')
        self.assertNotEqual(comment.author_id, self.user.pk)

    def test_public_comment_rejects_unpublished_content(self):
        draft = Dynamic.objects.create(
            author=self.user,
            title='草稿',
            content='尚未公开',
            status='draft',
        )

        response = self.client.post('/blog/comments/', {
            'dynamic_id': draft.pk,
            'content': '不应写入',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Comment.objects.filter(content='不应写入').exists())
