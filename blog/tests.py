import os
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

from blog.env import env_bool, env_list


class EnvironmentParsingTests(SimpleTestCase):
    def test_env_bool_parses_false_values(self):
        with patch.dict(os.environ, {'FEATURE_FLAG': 'false'}):
            self.assertFalse(env_bool('FEATURE_FLAG', True))

    def test_env_bool_uses_default_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(env_bool('FEATURE_FLAG', True))

    def test_env_list_trims_and_ignores_empty_items(self):
        with patch.dict(os.environ, {'HOSTS': 'blog.example.com, api.example.com, '}):
            self.assertEqual(
                env_list('HOSTS'),
                ['blog.example.com', 'api.example.com'],
            )


class ProductionUrlTests(SimpleTestCase):
    def test_debug_url_is_not_public(self):
        with self.assertRaises(Resolver404):
            resolve('/debug/urls/')

    def test_blog_test_url_is_not_public(self):
        with self.assertRaises(Resolver404):
            resolve('/blog/test/')
