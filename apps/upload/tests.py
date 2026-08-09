import io
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from apps.upload.models import UploadFile
from apps.upload.views import ensure_upload_directories


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
