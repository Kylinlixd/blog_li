from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.comment.models import Comment, CommentReadReceipt, CommentReadState
from apps.comment.device import parse_client_metadata
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

    def test_authenticated_public_comment_uses_the_logged_in_author_and_avatar(self):
        self.user.nickname = '站点作者'
        self.user.avatar = '/media/avatars/author.png'
        self.user.save(update_fields=['nickname', 'avatar'])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(self.user)}')

        response = self.client.post('/api/blog/comments/', {
            'dynamic_id': self.dynamic.pk,
            'content': '博主回复读者',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment = Comment.objects.get(content='博主回复读者')
        self.assertEqual(comment.author_id, self.user.pk)
        self.assertEqual(comment.nickname, '站点作者')
        self.assertEqual(response.data['data']['nickname'], '站点作者')
        self.assertEqual(response.data['data']['avatar'], '/media/avatars/author.png')


    def test_public_comment_records_and_returns_client_system_and_browser(self):
        user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/150.0.0.0 Safari/537.36'
        )
        response = self.client.post(
            '/api/blog/comments/',
            {
                'dynamic_id': self.dynamic.pk,
                'content': '带客户端信息的评论',
                'nickname': '匿名用户',
            },
            format='json',
            HTTP_USER_AGENT=user_agent,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment = Comment.objects.get(content='带客户端信息的评论')
        self.assertEqual(comment.client_os, 'Windows 10.0')
        self.assertEqual(comment.client_browser, 'Chrome150.0')
        self.assertEqual(response.data['data']['client_os'], 'Windows 10.0')
        self.assertEqual(response.data['data']['client_browser'], 'Chrome150.0')

    def test_client_metadata_parser_handles_mobile_safari_and_unknown_agents(self):
        self.assertEqual(
            parse_client_metadata(
                'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) '
                'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 '
                'Mobile/15E148 Safari/604.1'
            ),
            ('iOS 18.0', 'Safari18.0'),
        )
        self.assertEqual(
            parse_client_metadata(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/152.0.0.0 Safari/537.36'
            ),
            ('macOS', 'Chrome152.0'),
        )
        self.assertEqual(parse_client_metadata(''), ('', ''))

    def test_public_comment_accepts_optional_website_and_returns_it_for_approved_comments(self):
        response = self.client.post('/api/blog/comments/', {
            'dynamic_id': self.dynamic.pk,
            'content': '带主页的评论',
            'website': 'https://example.com/profile',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment = Comment.objects.get(content='带主页的评论')
        self.assertEqual(comment.website, 'https://example.com/profile')
        listed = self.client.get('/api/blog/comments/', {'dynamic_id': self.dynamic.pk})
        item = next(row for row in listed.data['data']['list'] if row['content'] == '带主页的评论')
        self.assertEqual(item['website'], 'https://example.com/profile')

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


class CommentNotificationTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username='moderator', email='moderator@example.com', role='admin')
        self.author = get_user_model().objects.create_user(username='visitor', email='visitor@example.com')
        self.dynamic = Dynamic.objects.create(author=self.admin, title='通知文章', content='正文', status='published')
        self.comment = Comment.objects.create(author=self.author, dynamic=self.dynamic, content='新评论', status='approved')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(self.admin)}')

    def test_unread_summary_counts_new_comments_but_excludes_own_comments(self):
        response = self.client.get('/api/comments/unread-summary/')
        self.assertEqual(response.data['data']['unread_count'], 1)
        Comment.objects.create(author=self.admin, dynamic=self.dynamic, content='自己的评论', status='approved')
        response = self.client.get('/api/comments/unread-summary/')
        self.assertEqual(response.data['data']['unread_count'], 1)

    def test_mark_read_is_idempotent_and_returns_remaining_count(self):
        response = self.client.post('/api/comments/mark-read/', {'ids': [self.comment.pk]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['unread_count'], 0)
        self.assertEqual(CommentReadReceipt.objects.filter(user=self.admin, comment=self.comment).count(), 1)
        again = self.client.post('/api/comments/mark-read/', {'ids': [self.comment.pk]}, format='json')
        self.assertEqual(again.data['data']['marked'], 0)

    def test_latest_id_cursor_keeps_newer_comments_unread(self):
        response = self.client.post('/api/comments/mark-read/', {'latest_comment_id': self.comment.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state = CommentReadState.objects.get(user=self.admin)
        self.assertEqual(state.last_seen_comment_id, self.comment.pk)
        newer = Comment.objects.create(author=self.author, dynamic=self.dynamic, content='后来评论', status='approved')
        summary = self.client.get('/api/comments/unread-summary/')
        self.assertEqual(summary.data['data']['unread_count'], 1)
        self.assertEqual(summary.data['data']['latest_comment_id'], newer.pk)

    def test_unread_list_is_scoped_to_current_user_and_marks_rows(self):
        response = self.client.get('/api/comments/?unread=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['total'], 1)
        self.assertTrue(response.data['data']['list'][0]['is_unread'])

    def test_public_path_cannot_access_notification_actions(self):
        response = self.client.get('/api/blog/comments/unread-summary/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
