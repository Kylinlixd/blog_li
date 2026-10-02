"""sitemap / RSS / robots 的契约测试：匿名可访问且内容随已发布文章变化。"""

from django.test import TestCase

from apps.dynamic.models import Dynamic
from apps.user.models import User


class SeoEndpointsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(username='seo-author', password='seo-pass-123')

    def _create_published_article(self, title='SEO 文章'):
        return Dynamic.objects.create(
            author=self.author,
            title=title,
            content='这是正文内容，用于 RSS 摘要。',
            status='published',
        )

    def test_robots_txt_points_to_sitemap(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('User-agent: *', body)
        self.assertIn('Sitemap: ', body)
        self.assertIn('Disallow: /admin/', body)

    def test_sitemap_lists_published_article_and_static_pages(self):
        article = self._create_published_article()
        Dynamic.objects.create(author=self.author, title='草稿', content='草稿', status='draft')

        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn(f'/blog/dynamics/{article.id}', body)
        self.assertNotIn('草稿', body)
        self.assertIn('/blog/blogdynamic', body)

    def test_rss_feed_contains_latest_published_article(self):
        article = self._create_published_article(title='订阅源里的文章')

        response = self.client.get('/feed.xml')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('订阅源里的文章', body)
        self.assertIn(f'/blog/dynamics/{article.id}', body)
