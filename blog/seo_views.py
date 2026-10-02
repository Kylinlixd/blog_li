"""SEO 入口：sitemap.xml / robots.txt / feed.xml（RSS 2.0）。

三个视图都是匿名可访问的纯 Django 视图（不经 DRF），站点根地址取
settings.PUBLIC_SITE_URL（环境变量 PUBLIC_SITE_URL，默认线上域名），
不依赖请求头拼接，方便 CDN / 反代缓存。
"""

import re

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import View
from xml.sax.saxutils import escape

from apps.category.models import Category
from apps.dynamic.models import Dynamic
from apps.tag.models import Tag

SITEMAP_CACHE_SECONDS = 60 * 15


def _site_url():
    return (getattr(settings, 'PUBLIC_SITE_URL', '') or '').rstrip('/')


def _xml_response(content):
    return HttpResponse(content, content_type='application/xml; charset=utf-8')


def _strip_markdown(content, limit=260):
    """RSS description 用：去掉常见 Markdown 记号后截断。"""
    text = re.sub(r'[#>*`~\[\]!]|!\[[^\]]*\]', '', content or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit]


@method_decorator(cache_page(SITEMAP_CACHE_SECONDS), name='dispatch')
class SitemapView(View):
    """手工拼装 sitemap 协议（urlset），静态页 + 文章 + 标签 + 分类。"""

    STATIC_PAGES = (
        ('/blog', 'daily', '1.0'),
        ('/blog/blogdynamic', 'daily', '0.9'),
        ('/blog/categories', 'weekly', '0.6'),
        ('/blog/about', 'monthly', '0.4'),
    )

    def get(self, request, *args, **kwargs):
        site = _site_url()
        entries = []

        for path, changefreq, priority in self.STATIC_PAGES:
            entries.append((f'{site}{path}', None, changefreq, priority))

        for article in (Dynamic.objects.filter(status='published')
                        .only('id', 'updated_at').order_by('-updated_at')):
            entries.append((
                f'{site}/blog/dynamics/{article.id}',
                article.updated_at.strftime('%Y-%m-%d'),
                'weekly',
                '0.8'
            ))

        for tag in Tag.objects.filter(status='active').only('id'):
            entries.append((f'{site}/blog/tags/{tag.id}', None, 'weekly', '0.5'))

        for category in Category.objects.filter(status='active').only('id'):
            entries.append((f'{site}/blog/categories/{category.id}', None, 'weekly', '0.5'))

        body = ['<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for loc, lastmod, changefreq, priority in entries:
            entry = [f'  <url>', f'    <loc>{escape(loc)}</loc>']
            if lastmod:
                entry.append(f'    <lastmod>{lastmod}</lastmod>')
            entry.append(f'    <changefreq>{changefreq}</changefreq>')
            entry.append(f'    <priority>{priority}</priority>')
            entry.append('  </url>')
            body.extend(entry)
        body.append('</urlset>')

        return _xml_response('\n'.join(body))


class ArticleFeed(Feed):
    """RSS 2.0：最近 20 篇已发布文章。"""

    title = '时不语之间'
    link = '/blog/'
    description = '时不语之间 · 个人博客的最新文章'

    def items(self):
        return (Dynamic.objects.filter(status='published')
                .only('id', 'title', 'content', 'created_at')
                .order_by('-created_at')[:20])

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return _strip_markdown(item.content)

    def item_link(self, item):
        # 相对路径即可，syndication 会按请求 Host 拼成绝对地址
        return f'/blog/dynamics/{item.id}'

    def item_pubdate(self, item):
        return item.created_at


def robots_txt(request):
    site = _site_url()
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /admin/',
        'Disallow: /dashboard',
        'Disallow: /api/',
        '',
        f'Sitemap: {site}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
