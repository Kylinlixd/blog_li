"""Storage boundary shared by upload, download and delete views."""

import hashlib
import os
import re
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from astrastore_xion import XionClient, XionConfig, XionError, XionHTTPError
from django.conf import settings


class StorageError(Exception):
    """Base error for blog storage operations."""


class StorageUnavailable(StorageError):
    """The configured storage backend is not currently available."""


class StorageNotFound(StorageError):
    """The physical file is already absent."""


@dataclass(frozen=True)
class StoredObject:
    storage_backend: str
    storage_key: str
    size: int
    checksum: str
    content_type: str


@dataclass
class OpenedObject:
    stream: BinaryIO
    size: int
    content_type: str

    def close(self):
        self.stream.close()


class LocalStorageBackend:
    name = "local"

    def save(self, uploaded_file, file_type):
        directory_name = _safe_file_type(file_type)
        suffix = _safe_suffix(uploaded_file.name)
        storage_key = f"{directory_name}/{uuid.uuid4().hex}{suffix}"
        target = _local_path(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        digest = hashlib.sha256()
        size = 0

        try:
            with open(temporary, "xb") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            os.replace(temporary, target)
        except OSError as error:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise StorageUnavailable("本地文件写入失败") from error

        return StoredObject(
            storage_backend=self.name,
            storage_key=storage_key,
            size=size,
            checksum=digest.hexdigest(),
            content_type=getattr(uploaded_file, "content_type", "")
            or "application/octet-stream",
        )

    def open(self, storage_key):
        target = _local_path(storage_key)
        try:
            stream = open(target, "rb")
        except FileNotFoundError as error:
            raise StorageNotFound("本地文件不存在") from error
        except OSError as error:
            raise StorageUnavailable("本地文件读取失败") from error
        return OpenedObject(
            stream=stream,
            size=target.stat().st_size,
            content_type="application/octet-stream",
        )

    def delete(self, storage_key):
        target = _local_path(storage_key)
        try:
            target.unlink()
        except FileNotFoundError:
            return
        except OSError as error:
            raise StorageUnavailable("本地文件删除失败") from error


class XionStorageBackend:
    name = "xion"

    def _client(self):
        return XionClient(XionConfig(
            api_gateway=settings.XION_BASE_URL,
            service_token=settings.XION_SERVICE_TOKEN,
            connect_timeout=settings.XION_CONNECT_TIMEOUT,
            read_timeout=settings.XION_READ_TIMEOUT,
            max_retries=settings.XION_MAX_RETRIES,
        ))

    def save(self, uploaded_file, file_type):
        client = self._client()
        try:
            response = client.upload_file(
                uploaded_file,
                Path(uploaded_file.name).name,
                {"file_type": _safe_file_type(file_type)},
            )
        except XionError as error:
            raise StorageUnavailable("AstraStoreXion 上传失败") from error
        finally:
            client.close()
        return StoredObject(
            storage_backend=self.name,
            storage_key=response.file_id,
            size=response.size,
            checksum=response.checksum,
            content_type=response.content_type,
        )

    def open(self, storage_key):
        client = self._client()
        temporary = tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
        try:
            status = client.get_file_status(storage_key)
            client.download_file(storage_key, temporary)
            temporary.seek(0)
        except XionHTTPError as error:
            temporary.close()
            if error.status_code == 404:
                raise StorageNotFound("AstraStoreXion 文件不存在") from error
            raise StorageUnavailable("AstraStoreXion 下载失败") from error
        except XionError as error:
            temporary.close()
            raise StorageUnavailable("AstraStoreXion 下载失败") from error
        finally:
            client.close()
        return OpenedObject(
            stream=temporary,
            size=status.size,
            content_type=status.content_type,
        )

    def delete(self, storage_key):
        client = self._client()
        try:
            client.delete_file(storage_key)
        except XionHTTPError as error:
            if error.status_code == 404:
                return
            raise StorageUnavailable("AstraStoreXion 删除失败") from error
        except XionError as error:
            raise StorageUnavailable("AstraStoreXion 删除失败") from error
        finally:
            client.close()


def get_storage_backend():
    if settings.XION_STORAGE_ENABLED:
        return XionStorageBackend()
    return LocalStorageBackend()


def backend_for_file(file_record):
    if file_record.storage_backend == "xion":
        return XionStorageBackend()
    return LocalStorageBackend()


def legacy_local_key(file_record):
    """Return a safe relative key for rows created before storage_key existed."""

    if file_record.storage_key:
        return file_record.storage_key
    media_prefix = settings.MEDIA_URL.rstrip("/") + "/"
    if not file_record.file_url.startswith(media_prefix):
        raise StorageUnavailable("历史文件URL不是本地媒体路径")
    return file_record.file_url[len(media_prefix):]


def _safe_file_type(value):
    return value if value in {"image", "video", "audio", "document", "other"} else "other"


def _safe_suffix(filename):
    suffix = Path(filename).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
        return ""
    return suffix


def _local_path(storage_key):
    if not storage_key or "\x00" in storage_key:
        raise StorageUnavailable("无效的本地存储标识")
    root = Path(settings.MEDIA_ROOT).resolve()
    target = (root / storage_key).resolve()
    if target == root or root not in target.parents:
        raise StorageUnavailable("本地存储标识越界")
    return target
