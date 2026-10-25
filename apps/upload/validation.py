import logging
import os

from django.conf import settings


logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    'audio': {'mp3', 'wav', 'ogg', 'oga', 'm4a', 'aac', 'flac'},
    'image': {'jpg', 'jpeg', 'png', 'gif', 'heic', 'heif'},
    'video': {'mp4', 'mov', 'm4v', 'avi', 'webm', 'hevc'},
    'document': {'pdf', 'doc', 'docx', 'xls', 'xlsx'},
}

ALLOWED_MIME_TYPES = {
    'audio': {
        'audio/mpeg',
        'audio/mp3',
        'audio/wav',
        'audio/x-wav',
        'audio/ogg',
        'audio/mp4',
        'audio/x-m4a',
        'audio/aac',
        'audio/flac',
        'audio/x-flac',
    },
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

# file_type='other' 不设白名单（zip/md/txt 等都应能传），但必须挡掉
# 浏览器同源可执行（html/svg）、系统双击可执行（exe/bat 等）和
# 服务端脚本（php/jsp 等）扩展名——它们一旦进入 /media/ 直出目录，
# 就是公开站点上的持久化脚本/钓鱼载体。
BLOCKED_OTHER_EXTENSIONS = {
    'html', 'htm', 'xhtml', 'svg',
    'exe', 'dll', 'com', 'scr', 'msi', 'bat', 'cmd', 'ps1',
    'vbs', 'vbe', 'wsf', 'wsh', 'hta',
    'php', 'phtml', 'jsp', 'jspx', 'asp', 'aspx', 'cgi',
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
    if extension == 'mp3':
        return header.startswith(b'ID3') or header[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2')
    if extension == 'wav':
        return header.startswith(b'RIFF') and header[8:12] == b'WAVE'
    if extension in {'ogg', 'oga'}:
        return header.startswith(b'OggS')
    if extension in {'m4a', 'aac'}:
        # m4a 是 ISO-BMFF；裸 aac 可能是 ADTS（\xff\xf1/\xff\xf9）
        return (len(header) >= 8 and header[4:8] == b'ftyp') or header[:2] in (b'\xff\xf1', b'\xff\xf9')
    if extension == 'flac':
        return header.startswith(b'fLaC')
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

    if file_type == 'other' and extension in BLOCKED_OTHER_EXTENSIONS:
        return False, '不支持上传可执行文件、网页或服务端脚本类型的文件'

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
