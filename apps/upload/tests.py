from unittest.mock import patch

from django.test import SimpleTestCase

from apps.upload.views import ensure_upload_directories


class UploadDirectoryTests(SimpleTestCase):
    def test_directory_initialization_tolerates_existing_directories(self):
        created = set()

        def create_directory(path, exist_ok=False):
            if path in created and not exist_ok:
                raise FileExistsError(path)
            created.add(path)

        with patch('apps.upload.views.os.path.exists', return_value=False), patch(
            'apps.upload.views.os.makedirs', side_effect=create_directory
        ):
            ensure_upload_directories()
            ensure_upload_directories()
