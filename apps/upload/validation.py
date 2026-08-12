import logging
import os

from django.conf import settings


logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    'image': {'jpg', 'jpeg', 'png', 'gif', 'heic', 'heif'},
    'video': {'mp4', 'mov', 'm4v', 'avi', 'webm', 'hevc'},
    'document': {'pdf', 'doc', 'docx', 'xls', 'xlsx'},
}

ALLOWED_MIME_TYPES = {
    'image': {'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/heic', 'image/heif'},
    'video': {'video/mp4', 'video/quicktime', 'video/x-m4v', 'video/x-msvideo', 'video/webm', 'video/hevc'},
    'document': {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    },
}


def _read_header(uploaded_file, size=16):
    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(size)
        uploaded_file.seek(0)
        return header
    except Exception:
        return b''


def _has_expected_signature(extension, header):
    if extension in {'jpg', 'jpeg'}:
        return header.startswith(b'\xff\xd8\xff')
    if extension == 'png':
        return header.startswith(b'\x89PNG\r\n\x1a\n')
    if extension == 'gif':
        return header.startswith((b'GIF87a', b'GIF89a'))
    if extension == 'hevc':
        # 裸 HEVC 码流没有 ISO-BMFF 的 ftyp 头，交给 ffmpeg 做最终解码校验。
        return True
    if extension in {'mp4', 'mov', 'm4v'}:
        return len(header) >= 8 and header[4:8] == b'ftyp'
    if extension in {'docx', 'xlsx'}:
        return header.startswith(b'PK\x03\x04')
    if extension in {'doc', 'xls'}:
        return header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
    if extension == 'pdf':
        return header.startswith(b'%PDF-')
    return True


def validate_file_type(file, file_type):
    extension = os.path.splitext(file.name)[1].lower().lstrip('.')
    if file_type in ALLOWED_EXTENSIONS and extension not in ALLOWED_EXTENSIONS[file_type]:
        return False, f'不支持的文件扩展名，请上传{file_type}类型的文件'

    content_type = (getattr(file, 'content_type', '') or '').lower()
    if file_type in ALLOWED_MIME_TYPES and content_type not in ALLOWED_MIME_TYPES[file_type]:
        return False, f'不支持的文件类型，请上传{file_type}类型的文件'

    if file_type in ALLOWED_EXTENSIONS and not _has_expected_signature(extension, _read_header(file)):
        logger.warning('文件内容与格式不符: extension=%s, content_type=%s', extension, content_type)
        return False, '文件内容与声明格式不符'
    return True, None


def validate_file_size(file, file_type):
    max_size = 2 * 1024 * 1024 if file_type == 'avatars' else settings.BLOG_FILE_MAX_UPLOAD_BYTES
    if file.size > max_size:
        return False, f'文件大小不能超过{max_size / 1024 / 1024}MB'
    return True, None
