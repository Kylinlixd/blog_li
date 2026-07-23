import os
from unittest.mock import patch

from django.test import SimpleTestCase
from django.test import RequestFactory
from django.http import HttpResponse
from django.core.cache import cache
from django.urls import Resolver404, resolve

from blog.env import env_bool, env_list
from blog.middleware import RequestIdMiddleware


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
    def test_public_blog_api_has_api_prefix_alias(self):
        match = resolve('/api/blog/tags/')

        self.assertEqual(match.url_name, 'api-blog-tags')

    def test_debug_url_is_not_public(self):
        with self.assertRaises(Resolver404):
            resolve('/debug/urls/')

    def test_blog_test_url_is_not_public(self):
        with self.assertRaises(Resolver404):
            resolve('/blog/test/')


class RequestIdMiddlewareTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.middleware = RequestIdMiddleware(lambda request: HttpResponse())

    def test_generated_request_id_is_available_to_errors_and_response(self):
        request = self.factory.get('/api/dynamics/')

        self.middleware.process_request(request)
        response = self.middleware.process_response(request, HttpResponse())

        self.assertTrue(request.request_id)
        self.assertEqual(response['X-Request-ID'], request.request_id)

    def test_duplicate_mutation_is_rejected_atomically(self):
        first = self.factory.post('/api/dynamics/', HTTP_X_REQUEST_ID='same-request')
        duplicate = self.factory.post('/api/dynamics/', HTTP_X_REQUEST_ID='same-request')

        self.assertIsNone(self.middleware.process_request(first))
        response = self.middleware.process_request(duplicate)

        self.assertEqual(response.status_code, 409)
