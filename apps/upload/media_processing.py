"""上传媒体的轻量处理边界。"""

import mimetypes
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


VIDEO_EXTENSIONS = {"mp4", "mov", "m4v", "avi", "webm", "hevc"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "heic", "heif"}

# 视频统一输出浏览器兼容的 H.264/AAC MP4，避免 iPhone HEVC 无法直接播放。
VIDEO_ARGUMENTS = [
    "-map",
    "0:v:0",
    "-map",
    "0:a?",
    "-vf",
    "scale=w='min(1920,iw)':h='min(1920,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
    "-c:v",
    "libx264",
    "-preset",
    "medium",
    "-crf",
    "23",
    "-pix_fmt",
    "yuv420p",
    "-c:a",
    "aac",
    "-b:a",
    "128k",
    "-movflags",
    "+faststart",
]


@dataclass
class ProcessedMedia:
    """描述临时处理结果，并负责统一清理临时目录。"""

    media_path: Path
    media_name: str
    content_type: str
    poster_path: Path | None
    poster_name: str
    poster_content_type: str
    temporary_directory: Path

    @property
    def media_content_type(self):
        """保留语义更明确的别名，便于调用方读取处理后媒体 MIME。"""
        return self.content_type

    def cleanup(self):
        """处理成功或失败后都删除临时输入、输出和封面。"""
        shutil.rmtree(self.temporary_directory, ignore_errors=True)


def _write_uploaded_file(uploaded_file, target: Path):
    with target.open("wb") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)


def _run_ffmpeg(command):
    return subprocess.run(
        command,
        check=True,
        timeout=300,
        capture_output=True,
        text=True,
    )


def process_uploaded_media(uploaded_file, file_type: str) -> ProcessedMedia:
    """把原始上传文件转换为可被网页稳定播放或展示的临时文件。"""
    temporary_directory = Path(tempfile.mkdtemp(prefix="blog-media-"))
    original_name = Path(getattr(uploaded_file, "name", "upload")).name
    suffix = Path(original_name).suffix.lower()
    extension = suffix.lstrip(".")
    source_path = temporary_directory / f"source{suffix or '.bin'}"
    _write_uploaded_file(uploaded_file, source_path)

    try:
        if file_type == "video" and extension in VIDEO_EXTENSIONS:
            media_path = temporary_directory / "media.mp4"
            poster_path = temporary_directory / "poster.jpg"
            _run_ffmpeg(["ffmpeg", "-y", "-i", str(source_path), *VIDEO_ARGUMENTS, str(media_path)])
            _run_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(media_path),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    str(poster_path),
                ]
            )
            return ProcessedMedia(
                media_path=media_path,
                media_name=f"{Path(original_name).stem}.mp4",
                content_type="video/mp4",
                poster_path=poster_path,
                poster_name=f"{Path(original_name).stem}.jpg",
                poster_content_type="image/jpeg",
                temporary_directory=temporary_directory,
            )

        if file_type == "image" and extension in {"heic", "heif"}:
            media_path = temporary_directory / "media.jpg"
            heif_converter = shutil.which("heif-convert")
            if heif_converter:
                # Ubuntu 的 FFmpeg 通常只有 HEVC 解码器，优先使用 libheif 工具读 HEIC 容器。
                _run_ffmpeg([heif_converter, "--quiet", str(source_path), str(media_path)])
            else:
                _run_ffmpeg(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(source_path),
                        "-frames:v",
                        "1",
                        "-q:v",
                        "2",
                        str(media_path),
                    ]
                )
            return ProcessedMedia(
                media_path=media_path,
                media_name=f"{Path(original_name).stem}.jpg",
                content_type="image/jpeg",
                poster_path=None,
                poster_name="",
                poster_content_type="",
                temporary_directory=temporary_directory,
            )

        media_path = temporary_directory / f"media{suffix or '.bin'}"
        shutil.copyfile(source_path, media_path)
        content_type = (
            getattr(uploaded_file, "content_type", "")
            or mimetypes.guess_type(original_name)[0]
            or "application/octet-stream"
        )
        return ProcessedMedia(
            media_path=media_path,
            media_name=original_name,
            content_type=content_type,
            poster_path=None,
            poster_name="",
            poster_content_type="",
            temporary_directory=temporary_directory,
        )
    except Exception:
        shutil.rmtree(temporary_directory, ignore_errors=True)
        raise
