import json
import logging
import os
import uuid

from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from apps.user.permissions import IsContentEditor
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import UploadFile, FileCategory, FileTag
from .serializers import (
    UploadFileSerializer, FileUploadSerializer,
    FileCategorySerializer, FileTagSerializer,
    FileListSerializer
)
from .storage_backends import (
    StorageNotFound,
    StorageUnavailable,
    backend_for_file,
    get_storage_backend,
    legacy_local_key,
)
from .media_processing import process_uploaded_media
from .validation import validate_file_size, validate_file_type

# 配置日志记录器
logger = logging.getLogger(__name__)


class FilePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

def ensure_upload_directories():
    """
    确保所有上传目录存在
    """
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    upload_types = ['image', 'video', 'document', 'other', 'avatars']
    for upload_type in upload_types:
        upload_dir = os.path.join(settings.MEDIA_ROOT, upload_type)
        os.makedirs(upload_dir, exist_ok=True)

# 在应用启动时创建目录
ensure_upload_directories()

class FileCategoryViewSet(ModelViewSet):
    """文件分类视图集"""
    queryset = FileCategory.objects.all()
    serializer_class = FileCategorySerializer
    permission_classes = [IsContentEditor]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset

class FileTagViewSet(ModelViewSet):
    """文件标签视图集"""
    queryset = FileTag.objects.all()
    serializer_class = FileTagSerializer
    permission_classes = [IsContentEditor]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset

class FileManagementViewSet(ModelViewSet):
    """文件管理视图集"""
    queryset = UploadFile.objects.all()
    serializer_class = UploadFileSerializer
    permission_classes = [IsContentEditor]
    pagination_class = FilePagination
    
    def get_queryset(self):
        queryset = UploadFile.objects.all()
        
        # 按类型过滤
        file_type = self.request.query_params.get('type')
        if file_type:
            queryset = queryset.filter(file_type=file_type)
            
        # 按上传者过滤
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            queryset = queryset.filter(uploader=self.request.user)
            
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(uploader=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # 检查权限
        if not request.user.is_staff and not request.user.is_superuser and instance.uploader != request.user:
            return Response(
                {"detail": "您没有权限删除此文件"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            backend = backend_for_file(instance)
            backend.delete(_storage_key(instance))
            if instance.poster_storage_key:
                poster_backend = backend_for_file(instance)
                poster_backend.delete(instance.poster_storage_key)
        except StorageNotFound:
            pass
        except StorageUnavailable as error:
            logger.warning("删除物理文件失败，保留数据库记录: %s", error)
            return Response({
                "code": 503,
                "message": "存储服务暂时不可用，文件记录已保留",
                "data": None
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        self.perform_destroy(instance)
        return Response({
            "code": 200,
            "message": "文件删除成功",
            "data": None
        })
    
    @action(detail=True, methods=['get', 'post'])
    def download(self, request, pk=None):
        """下载文件"""
        file_obj = self.get_object()
        response = _file_response(file_obj, as_attachment=True)
        if isinstance(response, Response):
            return response
        file_obj.increase_download_count()
        return response
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """搜索文件"""
        query = request.query_params.get('q', '')
        file_type = request.query_params.get('type')
        category_id = request.query_params.get('category')
        tag_ids = request.query_params.getlist('tags')
        
        queryset = self.get_queryset()
        
        # 搜索条件
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
        
        if file_type:
            queryset = queryset.filter(file_type=file_type)
            
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        if tag_ids:
            queryset = queryset.filter(tags__id__in=tag_ids).distinct()
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'data': {
                'items': serializer.data,
                'total': queryset.count()
            },
            'message': '搜索成功'
        })

# Create your views here.
class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, *args, **kwargs):
        try:
            if 'file' not in request.FILES:
                return Response({
                    'code': 400,
                    'message': '未提供文件'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            file = request.FILES['file']
            
            # 验证文件类型
            is_valid, error_message = validate_file_type(file, 'image')
            if not is_valid:
                return Response({
                    'code': 400,
                    'message': error_message
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 验证文件大小
            is_valid, error_message = validate_file_size(file, 'avatars')
            if not is_valid:
                return Response({
                    'code': 400,
                    'message': error_message
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 创建目录（如果不存在）
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
            os.makedirs(upload_dir, exist_ok=True)
            
            # 生成唯一文件名
            filename = f"{uuid.uuid4().hex}{os.path.splitext(file.name)[1]}"
            file_path = os.path.join(upload_dir, filename)
            
            # 保存文件
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            # 获取URL
            file_url = f"{settings.MEDIA_URL}avatars/{filename}"
            
            # 更新用户头像
            request.user.avatar = file_url
            request.user.save()
            
            return Response({
                'code': 200,
                'data': {
                    'url': file_url
                },
                'message': '头像上传成功'
            })
            
        except Exception as e:
            logger.exception('Avatar upload failed')
            return Response({
                'code': 500,
                'message': '文件上传失败，请稍后重试'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FileUploadView(APIView):
    permission_classes = [IsContentEditor]
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        backend = None
        stored = None
        poster_stored = None
        processed = None
        try:
            if 'file' not in request.FILES:
                return Response({
                    'code': 400,
                    'message': '未提供文件'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            file = request.FILES['file']
            file_type = request.data.get('file_type', 'other')
            valid_file_types = {choice[0] for choice in UploadFile.FILE_TYPE_CHOICES}
            if file_type not in valid_file_types:
                return Response({
                    'code': 400,
                    'message': '不支持的文件类型'
                }, status=status.HTTP_400_BAD_REQUEST)
            dynamic_id = request.data.get('dynamic_id')
            category_id = request.data.get('category_id')
            tag_ids = request.data.getlist('tag_ids')
            description = request.data.get('description', '')
            is_public = _parse_boolean(request.data.get('is_public', True))
            
            # 验证文件类型
            is_valid, error_message = validate_file_type(file, file_type)
            if not is_valid:
                logger.warning(f"文件类型验证失败: {error_message}")
                return Response({
                    'code': 400,
                    'message': error_message
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 验证文件大小
            is_valid, error_message = validate_file_size(file, file_type)
            if not is_valid:
                logger.warning(f"文件大小验证失败: {error_message}")
                return Response({
                    'code': 400,
                    'message': error_message
                }, status=status.HTTP_400_BAD_REQUEST)
            
            processed = process_uploaded_media(file, file_type)
            backend = get_storage_backend()

            # 存储边界只接收处理后的临时文件，原始 MOV/HEIC 不直接暴露给网页。
            with processed.media_path.open('rb') as media_stream:
                media_file = File(media_stream, name=processed.media_name)
                media_file.content_type = processed.content_type
                stored = backend.save(media_file, file_type)

            if processed.poster_path is not None:
                with processed.poster_path.open('rb') as poster_stream:
                    poster_file = File(poster_stream, name=processed.poster_name)
                    poster_file.content_type = processed.poster_content_type
                    poster_stored = backend.save(poster_file, 'image')

            with transaction.atomic():
                upload_file = UploadFile.objects.create(
                    name=processed.media_name,
                    file_type=file_type,
                    file_size=stored.size,
                    file_url='',
                    storage_backend=stored.storage_backend,
                    storage_key=stored.storage_key,
                    checksum=stored.checksum,
                    content_type=processed.content_type,
                    poster_storage_backend=poster_stored.storage_backend if poster_stored else '',
                    poster_storage_key=poster_stored.storage_key if poster_stored else '',
                    uploader=request.user,
                    category_id=category_id or None,
                    description=description,
                    is_public=is_public,
                )
                upload_file.file_url = _stable_file_url(upload_file)
                upload_file.poster_url = _stable_poster_url(upload_file) if poster_stored else ''
                upload_file.save(update_fields=['file_url'])
                if poster_stored:
                    upload_file.save(update_fields=['poster_url'])

                normalized_tags = _parse_tag_ids(tag_ids)
                if normalized_tags:
                    upload_file.tags.set(normalized_tags)

                if dynamic_id:
                    from apps.dynamic.models import Dynamic
                    try:
                        dynamic = Dynamic.objects.get(id=dynamic_id)
                    except Dynamic.DoesNotExist:
                        logger.warning("动态不存在: %s", dynamic_id)
                    else:
                        dynamic.files.add(upload_file)
            
            return Response({
                'code': 200,
                'data': UploadFileSerializer(upload_file).data,
                'message': '文件上传成功'
            })
            
        except StorageUnavailable as error:
            _delete_stored_objects(backend, stored, poster_stored)
            logger.warning("存储服务上传失败: %s", error)
            return Response({
                'code': 503,
                'message': '存储服务暂时不可用，请稍后重试'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as error:
            _delete_stored_objects(backend, stored, poster_stored)
            logger.error("文件上传失败: %s", error, exc_info=True)
            return Response({
                'code': 500,
                'message': '文件上传失败，请稍后重试'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if processed is not None:
                processed.cleanup()


class PublicFileDownloadView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        file_obj = get_object_or_404(UploadFile, pk=pk, is_public=True)
        response = _file_response(file_obj, as_attachment=False)
        if isinstance(response, Response):
            return response
        file_obj.increase_download_count()
        return response


class PublicFilePosterDownloadView(APIView):
    """公开视频封面响应，封面与主视频共用访问权限和存储后端。"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        file_obj = get_object_or_404(UploadFile, pk=pk, is_public=True)
        return _poster_response(file_obj)


class PrivateFilePosterDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        file_obj = get_object_or_404(UploadFile, pk=pk)
        if not request.user.is_staff and file_obj.uploader_id != request.user.id:
            return Response({'detail': '您没有权限查看此封面'}, status=status.HTTP_403_FORBIDDEN)
        return _poster_response(file_obj)


def _storage_key(file_obj):
    if file_obj.storage_backend == 'local':
        return legacy_local_key(file_obj)
    return file_obj.storage_key


def _file_response(file_obj, as_attachment):
    try:
        opened = backend_for_file(file_obj).open(_storage_key(file_obj))
    except StorageNotFound:
        return Response({
            'code': 404,
            'message': '文件不存在',
            'data': None,
        }, status=status.HTTP_404_NOT_FOUND)
    except StorageUnavailable:
        return Response({
            'code': 503,
            'message': '存储服务暂时不可用',
            'data': None,
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    content_type = file_obj.content_type or opened.content_type or 'application/octet-stream'
    safe_inline = content_type.lower().split(';', 1)[0].strip() in {
        'image/gif',
        'image/jpeg',
        'image/png',
        'audio/mpeg',
        'audio/mp4',
        'audio/ogg',
        'audio/wav',
        'audio/x-wav',
        'video/mp4',
        'video/quicktime',
        'video/webm',
    }
    response = FileResponse(
        opened.stream,
        as_attachment=as_attachment or not safe_inline,
        filename=file_obj.name,
    )
    response['Content-Type'] = content_type if safe_inline else 'application/octet-stream'
    response['Content-Length'] = str(opened.size)
    response['ETag'] = f'"sha256-{file_obj.checksum}"' if file_obj.checksum else ''
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def _poster_response(file_obj):
    if not file_obj.poster_storage_key:
        return Response({'code': 404, 'message': '封面不存在', 'data': None}, status=status.HTTP_404_NOT_FOUND)
    try:
        opened = backend_for_file(file_obj).open(file_obj.poster_storage_key)
    except StorageNotFound:
        return Response({'code': 404, 'message': '封面不存在', 'data': None}, status=status.HTTP_404_NOT_FOUND)
    except StorageUnavailable:
        return Response({'code': 503, 'message': '存储服务暂时不可用', 'data': None}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    response = FileResponse(opened.stream, as_attachment=False, filename=file_obj.name.rsplit('.', 1)[0] + '.jpg')
    response['Content-Type'] = 'image/jpeg'
    response['Content-Length'] = str(opened.size)
    response['ETag'] = f'"sha256-{file_obj.checksum}-poster"' if file_obj.checksum else ''
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def _stable_file_url(file_obj):
    if file_obj.is_public:
        return f'/api/upload/public/{file_obj.id}/'
    return f'/api/upload/files/{file_obj.id}/download/'


def _stable_poster_url(file_obj):
    """封面复用文件权限，单独走图片响应以保持视频主文件记录完整。"""
    if file_obj.is_public:
        return f'/api/upload/poster/{file_obj.id}/'
    return f'/api/upload/files/{file_obj.id}/poster/'


def _delete_stored_objects(backend, *stored_objects):
    """上传后任一步失败时删除已经写入的主文件和封面。"""
    if backend is None:
        return
    for stored_object in stored_objects:
        if stored_object is None:
            continue
        try:
            backend.delete(stored_object.storage_key)
        except Exception:
            logger.exception("存储补偿删除失败: %s", stored_object.storage_key)


def _parse_boolean(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _parse_tag_ids(values):
    if not values:
        return []
    if len(values) == 1 and isinstance(values[0], str) and values[0].lstrip().startswith('['):
        try:
            decoded = json.loads(values[0])
        except json.JSONDecodeError:
            return []
        return decoded if isinstance(decoded, list) else []
    return values
