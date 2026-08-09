import hashlib
import mimetypes
import os
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.upload.models import UploadFile


RUN_LIVE_XION = os.getenv("XION_INTEGRATION_TEST") == "1"


@skipUnless(RUN_LIVE_XION, "set XION_INTEGRATION_TEST=1 to run the live Xion lifecycle")
@override_settings(
    XION_STORAGE_ENABLED=True,
    XION_BASE_URL=os.getenv("XION_BASE_URL", "http://127.0.0.1:18081"),
    XION_SERVICE_TOKEN=os.getenv("XION_SERVICE_TOKEN", ""),
)
class LiveXionFileLifecycleTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="xion-integration",
            email="xion-integration@example.test",
            password="integration-only-password",
        )
        self.client.force_authenticate(self.user)

    def test_generated_fixtures_round_trip_through_blog_api(self):
        fixture_dir = Path(os.environ["XION_FIXTURE_DIR"])
        fixtures = [
            ("storage-test-cover.png", "image"),
            ("storage-client-guide.pdf", "document"),
            ("storage-integration-checklist.docx", "document"),
            ("upload-smoke.txt", "other"),
        ]

        for filename, file_type in fixtures:
            with self.subTest(filename=filename):
                path = fixture_dir / filename
                original = path.read_bytes()
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                response = self.client.post(
                    "/api/upload/upload/",
                    {
                        "file": SimpleUploadedFile(filename, original, content_type=content_type),
                        "file_type": file_type,
                        "is_public": "true",
                    },
                    format="multipart",
                )
                self.assertEqual(200, response.status_code, response.data)

                record = UploadFile.objects.get(id=response.data["data"]["id"])
                self.assertEqual("xion", record.storage_backend)
                self.assertEqual(hashlib.sha256(original).hexdigest(), record.checksum)

                download = self.client.post(f"/api/upload/files/{record.id}/download/")
                self.assertEqual(200, download.status_code)
                self.assertEqual(original, b"".join(download.streaming_content))

                deleted = self.client.delete(f"/api/upload/files/{record.id}/")
                self.assertEqual(200, deleted.status_code, deleted.data)
                self.assertFalse(UploadFile.objects.filter(id=record.id).exists())
