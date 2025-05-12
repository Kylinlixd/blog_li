from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from django.db.models import Q
from django.http import FileResponse
import os
import uuid
import mimetypes
import logging
from django.conf import settings
from .models import UploadFile, FileCategory, FileTag
from .serializers import (
    UploadFileSerializer, FileUploadSerializer,
    FileCategorySerializer, FileTagSerializer,
    FileListSerializer
)

# 配置日志记录器
logger = logging.getLogger(__name__)

def ensure_upload_directories():
    """
    确保所有上传目录存在
    """
    try:
        # 基础媒体目录
        if not os.path.exists(settings.MEDIA_ROOT):
            os.makedirs(settings.MEDIA_ROOT)
            logger.info(f"创建基础媒体目录: {settings.MEDIA_ROOT}")
        
        # 各种类型的上传目录
        upload_types = ['image', 'video', 'document', 'other', 'avatars']
        for upload_type in upload_types:
            upload_dir = os.path.join(settings.MEDIA_ROOT, upload_type)
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
                logger.info(f"创建目录: {upload_dir}")
    except Exception as e:
        logger.error(f"创建目录失败: {str(e)}")
        raise

# 在应用启动时创建目录
ensure_upload_directories()

def validate_file_type(file, file_type):
    """
    验证文件类型
    """
    try:
        # 获取文件的MIME类型
        content_type = file.content_type
        logger.debug(f"文件MIME类型: {content_type}")
        
        # 定义允许的文件类型
        allowed_types = {
            'image': ['image/jpeg', 'image/png', 'image/gif', 'image/jpg'],
            'video': ['video/mp4', 'video/quicktime', 'video/x-msvideo'],
            'document': [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ]
        }
        
        # 检查文件类型是否在允许列表中
        if file_type in allowed_types and content_type not in allowed_types[file_type]:
            logger.warning(f"不支持的文件类型: {content_type}, 期望类型: {file_type}")
            return False, f"不支持的文件类型，请上传{file_type}类型的文件"
        
        return True, None
    except Exception as e:
        logger.error(f"验证文件类型时出错: {str(e)}")
        return False, f"验证文件类型时出错: {str(e)}"

def validate_file_size(file, file_type):
    """
    验证文件大小
    """
    try:
        # 定义不同类型文件的大小限制（单位：字节）
        size_limits = {
            'image': 5 * 1024 * 1024,  # 5MB
            'video': 100 * 1024 * 1024,  # 100MB
            'document': 20 * 1024 * 1024,  # 20MB
            'other': 10 * 1024 * 1024,  # 10MB
            'avatars': 2 * 1024 * 1024  # 2MB
        }
        
        # 获取文件大小限制
        max_size = size_limits.get(file_type, size_limits['other'])
        logger.debug(f"文件大小: {file.size}, 限制大小: {max_size}")
        
        # 检查文件大小
        if file.size > max_size:
            logger.warning(f"文件大小超出限制: {file.size} > {max_size}")
            return False, f"文件大小不能超过{max_size/1024/1024}MB"
        
        return True, None
    except Exception as e:
        logger.error(f"验证文件大小时出错: {str(e)}")
        return False, f"验证文件大小时出错: {str(e)}"

class FileCategoryViewSet(ModelViewSet):
    """文件分类视图集"""
    queryset = FileCategory.objects.all()
    serializer_class = FileCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # 只返回启用状态的分类
        return queryset.filter(status=True)

class FileTagViewSet(ModelViewSet):
    """文件标签视图集"""
    queryset = FileTag.objects.all()
    serializer_class = FileTagSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # 只返回启用状态的标签
        return queryset.filter(status=True)

class FileManagementViewSet(ModelViewSet):
    """文件管理视图集"""
    queryset = UploadFile.objects.all()
    serializer_class = UploadFileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = UploadFile.objects.all()
        
        # 按类型过滤
        file_type = self.request.query_params.get('type')
        if file_type:
            queryset = queryset.filter(file_type=file_type)
            
        # 按分类过滤
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        # 按标签过滤
        tag_ids = self.request.query_params.getlist('tags')
        if tag_ids:
            queryset = queryset.filter(tags__id__in=tag_ids).distinct()
            
        # 按上传者过滤
        if not self.request.user.is_staff:
            queryset = queryset.filter(uploader=self.request.user)
            
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(uploader=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # 检查权限
        if not request.user.is_staff and instance.uploader != request.user:
            return Response(
                {"detail": "您没有权限删除此文件"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # 获取文件路径
            file_path = os.path.join(settings.MEDIA_ROOT, instance.file_url.replace(settings.MEDIA_URL, ''))
            
            # 删除数据库记录
            self.perform_destroy(instance)
            
            # 删除真实文件
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    logger.warning(f"删除物理文件失败: {str(e)}")
                    # 继续执行，因为数据库记录已经删除
                
            return Response({
                "code": 200,
                "message": "文件删除成功",
                "data": None
            })
            
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return Response({
                "code": 500,
                "message": "文件删除失败，请稍后重试",
                "data": None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """下载文件"""
        file_obj = self.get_object()
        
        # 增加下载次数
        file_obj.increase_download_count()
        
        # 获取文件路径
        file_path = os.path.join(settings.MEDIA_ROOT, file_obj.file_url.replace(settings.MEDIA_URL, ''))
        
        if not os.path.exists(file_path):
            return Response({
                'code': 404,
                'message': '文件不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 获取文件类型
        content_type, _ = mimetypes.guess_type(file_path)
        
        # 打开文件
        file = open(file_path, 'rb')
        response = FileResponse(file)
        response['Content-Type'] = content_type
        response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
        
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
            return Response({
                'code': 500,
                'message': f'文件上传失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        try:
            logger.info(f"开始处理文件上传请求: {request.FILES}")
            
            if 'file' not in request.FILES:
                return Response({
                    'code': 400,
                    'message': '未提供文件'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            file = request.FILES['file']
            file_type = request.data.get('file_type', 'other')
            dynamic_id = request.data.get('dynamic_id')
            category_id = request.data.get('category_id')
            tag_ids = request.data.getlist('tag_ids')
            description = request.data.get('description', '')
            is_public = request.data.get('is_public', True)
            
            logger.info(f"上传文件信息: 类型={file_type}, 大小={file.size}, 名称={file.name}")
            
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
            
            # 生成唯一文件名
            file_ext = os.path.splitext(file.name)[1]
            file_name = f"{uuid.uuid4()}{file_ext}"
            
            # 构建文件保存路径
            upload_dir = os.path.join(settings.MEDIA_ROOT, file_type)
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, file_name)
            
            logger.info(f"保存文件到: {file_path}")
            
            # 保存文件
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            # 构建文件URL
            file_url = f"{settings.MEDIA_URL}{file_type}/{file_name}"
            
            # 保存文件信息到数据库
            upload_file = UploadFile.objects.create(
                name=file.name,
                file_type=file_type,
                file_size=file.size,
                file_url=file_url,
                uploader=request.user,
                category_id=category_id,
                description=description,
                is_public=is_public
            )
            
            # 添加标签
            if tag_ids:
                upload_file.tags.set(tag_ids)
            
            # 如果提供了动态ID，则关联到动态
            if dynamic_id:
                try:
                    from apps.dynamic.models import Dynamic
                    dynamic = Dynamic.objects.get(id=dynamic_id)
                    dynamic.files.add(upload_file)
                    logger.info(f"文件已关联到动态: {dynamic_id}")
                except Dynamic.DoesNotExist:
                    logger.warning(f"动态不存在: {dynamic_id}")
                except Exception as e:
                    logger.error(f"关联文件到动态时出错: {str(e)}")
            
            logger.info(f"文件上传成功: {file_url}")
            
            return Response({
                'code': 200,
                'data': UploadFileSerializer(upload_file).data,
                'message': '文件上传成功'
            })
            
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': f'文件上传失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
