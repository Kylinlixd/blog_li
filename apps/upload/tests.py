import importlib
import importlib.util
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APITestCase

from apps.upload.models import UploadFile
from apps.upload.storage_backends import OpenedObject, StoredObject, StorageUnavailable
from apps.upload.views import ensure_upload_directories, validate_file_size


class UploadDirectoryTests(SimpleTestCase):
    def test_directory_initialization_tolerates_existing_directories(self):
        created = set()

        def create_directory(path, exist_ok=False):
            if path in created and not exist_ok:
                raise FileExistsError(path)
            created.add(path)

        with patch("apps.upload.views.os.path.exists", return_value=False), patch(
            "apps.upload.views.os.makedirs", side_effect=create_directory
        ):
            ensure_upload_directories()
            ensure_upload_directories()


class UploadSizeContractTests(SimpleTestCase):
    def test_all_file_types_share_the_public_50_mb_limit(self):
        maximum = 50 * 1024 * 1024

        for file_type in ("image", "video", "document", "other"):
            with self.subTest(file_type=file_type):
                self.assertEqual(
                    (True, None),
                    validate_file_size(SimpleNamespace(size=maximum), file_type),
                )
                allowed, message = validate_file_size(SimpleNamespace(size=maximum + 1), file_type)
                self.assertFalse(allowed)
                self.assertIn("50.0MB", message)


class UploadFileStorageModelTests(TestCase):
    def test_legacy_rows_default_to_local_storage(self):
        field = UploadFile._meta.get_field("storage_backend")

        self.assertEqual("local", field.default)
        self.assertTrue(UploadFile._meta.get_field("storage_key").null)
        self.assertTrue(UploadFile._meta.get_field("checksum").blank)


class StorageBackendTests(SimpleTestCase):
    @override_settings(
        XION_STORAGE_ENABLED=True,
        XION_BASE_URL="http://127.0.0.1:8081",
        XION_SERVICE_TOKEN="secret",
    )
    @patch("apps.upload.storage_backends.XionClient")
    def test_xion_backend_returns_storage_identity(self, client_type):
        from apps.upload.storage_backends import XionStorageBackend

        client = client_type.return_value
        client.upload_file.return_value = SimpleNamespace(
            file_id="b8c21d60-e970-4df5-890b-0d2dba93a654",
            checksum="abc",
            size=3,
            content_type="text/plain",
        )
        backend = XionStorageBackend()

        stored = backend.save(
            SimpleUploadedFile("a.txt", b"abc", content_type="text/plain"),
            "document",
        )

        self.assertEqual("xion", stored.storage_backend)
        self.assertEqual("b8c21d60-e970-4df5-890b-0d2dba93a654", stored.storage_key)
        self.assertEqual("abc", stored.checksum)
        client.upload_file.assert_called_once()
        client.close.assert_called_once_with()

    def test_local_backend_writes_relative_safe_key_and_checksum(self):
        from apps.upload.storage_backends import LocalStorageBackend

        with tempfile.TemporaryDirectory() as media_root, override_settings(
            MEDIA_ROOT=media_root,
            MEDIA_URL="/media/",
        ):
            backend = LocalStorageBackend()
            stored = backend.save(
                SimpleUploadedFile("../../a.txt", b"abc", content_type="text/plain"),
                "document",
            )

            self.assertEqual("local", stored.storage_backend)
            self.assertTrue(stored.storage_key.startswith("document/"))
            self.assertNotIn("..", stored.storage_key)
            self.assertEqual(
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                stored.checksum,
            )
            self.assertTrue(os.path.exists(os.path.join(media_root, stored.storage_key)))

    @override_settings(XION_STORAGE_ENABLED=False)
    def test_feature_flag_selects_local_backend(self):
        from apps.upload.storage_backends import LocalStorageBackend, get_storage_backend

        self.assertIsInstance(get_storage_backend(), LocalStorageBackend)

    @override_settings(
        XION_STORAGE_ENABLED=True,
        XION_BASE_URL="http://127.0.0.1:8081",
        XION_SERVICE_TOKEN="secret",
    )
    def test_feature_flag_selects_xion_backend(self):
        from apps.upload.storage_backends import XionStorageBackend, get_storage_backend

        self.assertIsInstance(get_storage_backend(), XionStorageBackend)


class XionConfigurationCheckTests(SimpleTestCase):
    @override_settings(
        XION_STORAGE_ENABLED=True,
        XION_BASE_URL="http://127.0.0.1:8081",
        XION_SERVICE_TOKEN="",
    )
    def test_enabled_xion_requires_service_token(self):
        from apps.upload.checks import check_xion_storage_settings

        errors = check_xion_storage_settings(None)

        self.assertEqual(["upload.E001"], [error.id for error in errors])

    @override_settings(
        XION_STORAGE_ENABLED=False,
        XION_BASE_URL="",
        XION_SERVICE_TOKEN="",
    )
    def test_disabled_xion_does_not_require_configuration(self):
        from apps.upload.checks import check_xion_storage_settings

        self.assertEqual([], check_xion_storage_settings(None))

    @override_settings(
        XION_STORAGE_ENABLED=True,
        XION_BASE_URL="http://127.0.0.1:8081",
        XION_SERVICE_TOKEN="",
    )
    def test_regular_system_check_rejects_enabled_xion_without_token(self):
        with self.assertRaises(SystemCheckError):
            call_command("check", verbosity=0)

    @override_settings(
        XION_STORAGE_ENABLED=True,
        XION_BASE_URL="http://127.0.0.1:8081",
        XION_SERVICE_TOKEN="",
    )
    def test_application_startup_rejects_enabled_xion_without_token(self):
        from apps.upload.apps import UploadConfig

        config = UploadConfig("apps.upload", importlib.import_module("apps.upload"))
        with self.assertRaises(ImproperlyConfigured):
            config.ready()


class HTTPSStorageSmokeContractTests(SimpleTestCase):
    def test_duplicate_nosniff_headers_from_app_and_proxy_are_accepted(self):
        script_path = Path(__file__).resolve().parents[2] / "ops" / "https-storage-smoke.py"
        spec = importlib.util.spec_from_file_location("https_storage_smoke", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        response = SimpleNamespace(headers={
            "Content-Disposition": "inline; filename=cover.png",
            "Content-Type": "image/png",
            "X-Content-Type-Options": "nosniff, nosniff",
        })

        module.require_public_headers(response, "cover.png")


class FileStorageViewTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="storage-editor",
            email="storage-editor@example.com",
            password="safe-password-123",
        )
        self.client.force_authenticate(self.user)

    @patch("apps.upload.views.get_storage_backend")
    def test_upload_persists_storage_identity_and_stable_url(self, backend_factory):
        backend_factory.return_value.save.return_value = StoredObject(
            storage_backend="xion",
            storage_key="b8c21d60-e970-4df5-890b-0d2dba93a654",
            size=3,
            checksum="abc",
            content_type="text/plain",
        )

        response = self.client.post("/api/upload/upload/", {
            "file": SimpleUploadedFile("a.txt", b"abc", content_type="text/plain"),
            "file_type": "other",
            "is_public": "true",
        })

        self.assertEqual(200, response.status_code)
        uploaded = UploadFile.objects.get()
        self.assertEqual("xion", uploaded.storage_backend)
        self.assertEqual("b8c21d60-e970-4df5-890b-0d2dba93a654", uploaded.storage_key)
        self.assertEqual("abc", uploaded.checksum)
        self.assertEqual(f"/api/upload/public/{uploaded.id}/", uploaded.file_url)
        self.assertEqual("xion", response.data["data"]["storage_backend"])

    @patch("apps.upload.views.get_storage_backend")
    def test_upload_rejects_unknown_file_type_before_storage(self, backend_factory):
        response = self.client.post("/api/upload/upload/", {
            "file": SimpleUploadedFile("a.txt", b"abc", content_type="text/plain"),
            "file_type": "../../escape",
        })

        self.assertEqual(400, response.status_code)
        backend_factory.assert_not_called()

    @patch("apps.upload.views.UploadFile.objects.create")
    @patch("apps.upload.views.get_storage_backend")
    def test_database_failure_deletes_new_storage_object(self, backend_factory, create):
        backend = backend_factory.return_value
        backend.save.return_value = StoredObject(
            "xion",
            "b8c21d60-e970-4df5-890b-0d2dba93a654",
            3,
            "abc",
            "text/plain",
        )
        create.side_effect = DatabaseError("database unavailable")

        response = self.client.post("/api/upload/upload/", {
            "file": SimpleUploadedFile("a.txt", b"abc", content_type="text/plain"),
            "file_type": "other",
        })

        self.assertEqual(500, response.status_code)
        backend.delete.assert_called_once_with("b8c21d60-e970-4df5-890b-0d2dba93a654")

    @patch("apps.upload.views.backend_for_file")
    def test_delete_failure_keeps_database_record(self, backend_factory):
        uploaded = self._create_file(storage_backend="xion", storage_key="xion-key")
        backend_factory.return_value.delete.side_effect = StorageUnavailable("down")

        response = self.client.delete(f"/api/upload/files/{uploaded.id}/")

        self.assertEqual(503, response.status_code)
        self.assertTrue(UploadFile.objects.filter(id=uploaded.id).exists())

    @patch("apps.upload.views.backend_for_file")
    def test_authenticated_download_streams_storage_content(self, backend_factory):
        uploaded = self._create_file(
            storage_backend="xion",
            storage_key="xion-key",
            content_type="text/plain",
        )
        backend_factory.return_value.open.return_value = OpenedObject(
            stream=tempfile.SpooledTemporaryFile(),
            size=3,
            content_type="text/plain",
        )
        backend_factory.return_value.open.return_value.stream.write(b"abc")
        backend_factory.return_value.open.return_value.stream.seek(0)

        response = self.client.post(f"/api/upload/files/{uploaded.id}/download/")

        self.assertEqual(200, response.status_code)
        self.assertEqual(b"abc", b"".join(response.streaming_content))
        self.assertEqual("application/octet-stream", response["Content-Type"])
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))
        self.assertEqual("nosniff", response["X-Content-Type-Options"])

    @patch("apps.upload.views.backend_for_file")
    def test_public_download_allows_anonymous_reader(self, backend_factory):
        uploaded = self._create_file(is_public=True)
        stream = tempfile.SpooledTemporaryFile()
        stream.write(b"public")
        stream.seek(0)
        backend_factory.return_value.open.return_value = OpenedObject(
            stream=stream,
            size=6,
            content_type="text/plain",
        )
        self.client.force_authenticate(user=None)

        response = self.client.get(f"/api/upload/public/{uploaded.id}/")

        self.assertEqual(200, response.status_code)
        self.assertEqual(b"public", b"".join(response.streaming_content))
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))
        self.assertEqual("application/octet-stream", response["Content-Type"])
        self.assertEqual("nosniff", response["X-Content-Type-Options"])

    @patch("apps.upload.views.backend_for_file")
    def test_public_safe_raster_image_can_render_inline(self, backend_factory):
        uploaded = self._create_file(
            name="cover.png",
            content_type="image/png",
            is_public=True,
        )
        stream = tempfile.SpooledTemporaryFile()
        stream.write(b"png")
        stream.seek(0)
        backend_factory.return_value.open.return_value = OpenedObject(
            stream=stream,
            size=3,
            content_type="image/png",
        )
        self.client.force_authenticate(user=None)

        response = self.client.get(f"/api/upload/public/{uploaded.id}/")

        self.assertEqual(200, response.status_code)
        self.assertEqual("image/png", response["Content-Type"])
        self.assertTrue(response["Content-Disposition"].startswith("inline;"))

    def test_file_list_honors_type_and_page_size_contract(self):
        for index in range(12):
            self._create_file(name=f"image-{index}.png", file_type="image")
        for index in range(3):
            self._create_file(name=f"document-{index}.pdf", file_type="document")

        response = self.client.get("/api/upload/files/?type=image&page_size=20")

        self.assertEqual(200, response.status_code)
        self.assertEqual(12, response.data["count"])
        self.assertEqual(12, len(response.data["results"]))

    def test_private_file_is_not_available_from_public_route(self):
        uploaded = self._create_file(is_public=False)
        self.client.force_authenticate(user=None)

        response = self.client.get(f"/api/upload/public/{uploaded.id}/")

        self.assertEqual(404, response.status_code)

    def _create_file(self, **overrides):
        values = {
            "name": "a.txt",
            "file_type": "other",
            "file_size": 3,
            "file_url": "/api/upload/private/placeholder/",
            "storage_backend": "local",
            "storage_key": "other/a.txt",
            "checksum": "abc",
            "content_type": "text/plain",
            "uploader": self.user,
            "is_public": False,
        }
        values.update(overrides)
        return UploadFile.objects.create(**values)
