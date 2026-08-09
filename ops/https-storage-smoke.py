#!/usr/bin/env python3
"""Exercise the production HTTPS, JWT, Django, and Xion path end to end."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import secrets
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = (
    ("storage-test-cover.png", "image"),
    ("storage-client-guide.pdf", "document"),
    ("storage-integration-checklist.docx", "document"),
    ("upload-smoke.txt", "other"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--fixture-dir", required=True, type=Path)
    parser.add_argument("--timeout", default=300, type=float)
    return parser.parse_args()


def bootstrap_django():
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog.settings")
    import django

    django.setup()


def require_response(response: requests.Response, expected: int, operation: str):
    if response.status_code != expected:
        raise RuntimeError(f"{operation} returned {response.status_code}: {response.text[:300]}")


def require_public_headers(response: requests.Response, filename: str):
    disposition = response.headers.get("Content-Disposition", "").lower()
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    if response.headers.get("X-Content-Type-Options", "").lower() != "nosniff":
        raise RuntimeError(f"missing nosniff header: {filename}")
    if filename.endswith(".png"):
        if not disposition.startswith("inline;") or content_type != "image/png":
            raise RuntimeError(f"safe image response headers mismatch: {filename}")
    elif not disposition.startswith("attachment;") or content_type != "application/octet-stream":
        raise RuntimeError(f"unsafe inline response headers mismatch: {filename}")


def main() -> int:
    args = parse_args()
    bootstrap_django()

    from django.contrib.auth import get_user_model

    from apps.upload.models import UploadFile
    from apps.upload.storage_backends import StorageNotFound, backend_for_file
    from apps.upload.views import _storage_key

    base_url = args.base_url.rstrip("/")
    suffix = uuid.uuid4().hex
    username = f"xion-https-smoke-{suffix}"
    password = secrets.token_urlsafe(32)
    user = get_user_model().objects.create(
        username=username,
        email=f"{username}@example.invalid",
        is_staff=True,
    )
    user.set_password(password)
    user.save(update_fields=["password"])
    session = requests.Session()
    created_ids: list[int] = []

    try:
        login = session.post(
            base_url + "/api/auth/login/",
            json={"username": username, "password": password},
            timeout=args.timeout,
        )
        require_response(login, 200, "login")
        session.headers["Authorization"] = "Bearer " + login.json()["data"]["access"]

        for filename, file_type in FIXTURES:
            path = args.fixture_dir / filename
            original = path.read_bytes()
            digest = hashlib.sha256(original).hexdigest()
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            upload = session.post(
                base_url + "/api/upload/upload/",
                files={"file": (filename, original, content_type)},
                data={"file_type": file_type, "is_public": "true"},
                timeout=args.timeout,
            )
            require_response(upload, 200, f"upload {filename}")
            item = upload.json()["data"]
            if item.get("storage_backend") != "xion" or item.get("checksum") != digest:
                raise RuntimeError(f"storage metadata mismatch: {filename}")
            record_id = int(item["id"])
            created_ids.append(record_id)

            private = session.post(
                f"{base_url}/api/upload/files/{record_id}/download/",
                timeout=args.timeout,
            )
            require_response(private, 200, f"authenticated download {filename}")
            if private.content != original:
                raise RuntimeError(f"authenticated bytes mismatch: {filename}")

            public = session.get(
                f"{base_url}/api/upload/public/{record_id}/",
                timeout=args.timeout,
            )
            require_response(public, 200, f"public download {filename}")
            if public.content != original:
                raise RuntimeError(f"public bytes mismatch: {filename}")
            require_public_headers(public, filename)

        for record_id in list(created_ids):
            deleted = session.delete(
                f"{base_url}/api/upload/files/{record_id}/",
                timeout=args.timeout,
            )
            require_response(deleted, 200, f"delete {record_id}")
            created_ids.remove(record_id)
    finally:
        for record in UploadFile.objects.filter(id__in=created_ids, uploader=user):
            try:
                backend_for_file(record).delete(_storage_key(record))
            except StorageNotFound:
                pass
            record.delete()
        user.delete()
        session.close()

    scheme = urlsplit(base_url).scheme
    print(json.dumps({"transport": f"{scheme}+jwt", "records": len(FIXTURES), "result": "clean"}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"HTTPS storage smoke failed: {error}", file=sys.stderr)
        raise
