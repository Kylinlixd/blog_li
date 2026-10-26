from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.dynamic.models import Dynamic
from apps.dynamic.translations import TranslationUnavailable, split_markdown


def _published_dynamic(**overrides):
    username = overrides.pop("username", "translation-author")
    author = get_user_model().objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="x",
    )
    return Dynamic.objects.create(
        author=author,
        title=overrides.pop("title", "一篇关于缓存的文章"),
        content=overrides.pop("content", "缓存是性能的第一道墙。\n\n合理使用缓存能挡住大部分流量。"),
        status=overrides.pop("status", "published"),
        **overrides,
    )


class TranslationSplitTests(APITestCase):
    def test_split_keeps_code_fence_verbatim(self):
        content = "第一段说明。\n\n```python\nprint('hello')  # 不翻译\n```\n\n第二段说明。"
        segments = split_markdown(content)
        code = [text for is_code, text in segments if is_code]
        texts = [text for is_code, text in segments if not is_code]
        self.assertEqual(len(code), 1)
        self.assertIn("print('hello')", code[0])
        self.assertEqual(len(texts), 2)

    def test_split_merges_short_paragraphs(self):
        content = "短段一。\n\n短段二。\n\n短段三。"
        segments = split_markdown(content)
        self.assertEqual(len(segments), 1, "相邻短段应合并以减少上游请求")
        self.assertNotIn("```", segments[0][1])


class DynamicTranslationApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.dynamic = _published_dynamic()

    def _get(self, lang="en", pk=None):
        return self.client.get(f"/api/blog/dynamics/{pk or self.dynamic.pk}/translation/", {"lang": lang})

    @patch("apps.dynamic.translations.translate_title_and_content")
    def test_generates_then_serves_from_cache(self, mock_translate):
        mock_translate.return_value = ("A post about caching", "Caching is the first wall.\n\nIt blocks most traffic.")
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "A post about caching")
        self.assertEqual(response.data["data"]["lang"], "en")
        self.assertEqual(mock_translate.call_count, 1)

        again = self._get()
        self.assertEqual(again.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_translate.call_count, 1, "第二次必须命中缓存，不再调用翻译")

    @override_settings(TRANSLATION_IP_COOLDOWN=0)
    @patch("apps.dynamic.translations.translate_title_and_content")
    def test_each_language_is_cached_independently(self, mock_translate):
        mock_translate.side_effect = lambda title, content, lang: (f"Title-{lang}", f"Body-{lang}")
        self.assertEqual(self._get("en").data["data"]["lang"], "en")
        self.assertEqual(self._get("ja").data["data"]["lang"], "ja")
        self.assertEqual(mock_translate.call_count, 2)

    def test_requires_lang_and_rejects_unknown(self):
        self.assertEqual(self.client.get(f"/api/blog/dynamics/{self.dynamic.pk}/translation/").status_code, 400)
        self.assertEqual(self._get("xx").status_code, 400)

    def test_draft_and_missing_article_404(self):
        draft = _published_dynamic(status="draft", username="translation-draft")
        self.assertEqual(self._get(pk=draft.pk).status_code, 404)
        self.assertEqual(self._get(pk=999999).status_code, 404)

    @patch("apps.dynamic.translations.translate_title_and_content")
    def test_daily_cap_returns_429(self, mock_translate):
        mock_translate.return_value = ("t", "b")
        with self.settings(TRANSLATION_DAILY_CAP=0):
            response = self._get()
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @patch("apps.dynamic.translations.translate_title_and_content")
    def test_ip_cooldown_returns_429(self, mock_translate):
        mock_translate.return_value = ("t", "b")
        first = self._get()
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        second = self._get("ja")
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @patch("apps.dynamic.translations.translate_title_and_content")
    def test_provider_failure_returns_503(self, mock_translate):
        mock_translate.side_effect = TranslationUnavailable("翻译服务暂时不可用，请稍后再试")
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
