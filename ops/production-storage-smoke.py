#!/usr/bin/env python3
"""Run a restart-safe production smoke test for the blog/Xion integration.

The command intentionally uses Django's in-process API client so no reusable
administrator credentials are required.  It creates an unusable temporary user
and writes only non-secret record identifiers to a mode-0600 state file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


FIXTURES = (
    ("storage-test-cover.png", "image"),
    ("storage-client-guide.pdf", "document"),
    ("storage-integration-checklist.docx", "document"),
    ("upload-smoke.txt", "other"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("create", "verify", "delete"))
    parser.add_argument("--fixture-dir", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    return parser.parse_args()


def bootstrap_django():
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog.settings")
    import django

    django.setup()


def fixture_bytes(fixture_dir: Path, filename: str) -> bytes:
    path = fixture_dir / filename
    if not path.is_file():
        raise RuntimeError(f"missing fixture: {path}")
    return path.read_bytes()


def response_bytes(response) -> bytes:
    try:
        if getattr(response, "streaming", False):
            return b"".join(response.streaming_content)
        return bytes(response.content)
    finally:
        response.close()


def require_status(response, expected: int, operation: str):
    if response.status_code == expected:
        return
    detail = getattr(response, "data", None)
    raise RuntimeError(f"{operation} returned {response.status_code}: {detail!r}")


def write_state(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_state(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"missing smoke state: {path}")
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def create_phase(args: argparse.Namespace):
    if args.state.exists():
        raise RuntimeError(f"refusing to overwrite existing smoke state: {args.state}")

    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile
    from rest_framework.test import APIClient

    from apps.upload.models import UploadFile

    suffix = uuid.uuid4().hex
    username = f"xion-smoke-{suffix}"
    user = get_user_model().objects.create(
        username=username,
        email=f"{username}@example.invalid",
        is_staff=True,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])

    client = APIClient(HTTP_HOST="127.0.0.1")
    client.force_authenticate(user)
    records = []
    try:
        for filename, file_type in FIXTURES:
            original = fixture_bytes(args.fixture_dir, filename)
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            response = client.post(
                "/api/upload/upload/",
                {
                    "file": SimpleUploadedFile(filename, original, content_type=content_type),
                    "file_type": file_type,
                    "is_public": "true",
                },
                format="multipart",
                secure=True,
            )
            require_status(response, 200, f"upload {filename}")
            record = UploadFile.objects.get(id=response.data["data"]["id"])
            digest = hashlib.sha256(original).hexdigest()
            if record.storage_backend != "xion" or record.checksum != digest:
                raise RuntimeError(f"storage metadata mismatch for {filename}")
            records.append({
                "id": record.id,
                "filename": filename,
                "sha256": digest,
                "storage_key": record.storage_key,
            })
    except Exception:
        for record in UploadFile.objects.filter(uploader=user):
            client.delete(f"/api/upload/files/{record.id}/", secure=True)
        user.delete()
        raise

    write_state(args.state, {"username": username, "user_id": user.id, "records": records})
    print(json.dumps({"phase": "create", "records": len(records), "backend": "xion"}))


def verify_records(args: argparse.Namespace, state: dict):
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    from apps.upload.models import UploadFile

    user = get_user_model().objects.get(id=state["user_id"], username=state["username"])
    authenticated = APIClient(HTTP_HOST="127.0.0.1")
    authenticated.force_authenticate(user)
    public = APIClient(HTTP_HOST="127.0.0.1")

    for item in state["records"]:
        original = fixture_bytes(args.fixture_dir, item["filename"])
        digest = hashlib.sha256(original).hexdigest()
        if digest != item["sha256"]:
            raise RuntimeError(f"fixture changed: {item['filename']}")

        record = UploadFile.objects.get(id=item["id"], uploader=user)
        if record.storage_backend != "xion" or record.storage_key != item["storage_key"]:
            raise RuntimeError(f"database metadata changed: {item['filename']}")

        download = authenticated.post(
            f"/api/upload/files/{record.id}/download/",
            secure=True,
        )
        require_status(download, 200, f"authenticated download {item['filename']}")
        if response_bytes(download) != original:
            raise RuntimeError(f"authenticated bytes mismatch: {item['filename']}")

        public_download = public.get(f"/api/upload/public/{record.id}/", secure=True)
        require_status(public_download, 200, f"public download {item['filename']}")
        if response_bytes(public_download) != original:
            raise RuntimeError(f"public bytes mismatch: {item['filename']}")

    return user, authenticated


def verify_phase(args: argparse.Namespace):
    state = load_state(args.state)
    verify_records(args, state)
    print(json.dumps({"phase": "verify", "records": len(state["records"]), "result": "ok"}))


def delete_phase(args: argparse.Namespace):
    from apps.upload.models import UploadFile

    state = load_state(args.state)
    user, client = verify_records(args, state)
    for item in state["records"]:
        response = client.delete(f"/api/upload/files/{item['id']}/", secure=True)
        require_status(response, 200, f"delete {item['filename']}")
        if UploadFile.objects.filter(id=item["id"]).exists():
            raise RuntimeError(f"database record still exists: {item['filename']}")
    user.delete()
    args.state.unlink()
    print(json.dumps({"phase": "delete", "records": len(state["records"]), "result": "clean"}))


def main() -> int:
    args = parse_args()
    bootstrap_django()
    if args.phase == "create":
        create_phase(args)
    elif args.phase == "verify":
        verify_phase(args)
    else:
        delete_phase(args)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"production storage smoke failed: {error}", file=sys.stderr)
        raise
