from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
import os
import uuid
import mimetypes
import logging
from django.conf import settings
from .models import UploadFile
from .serializers import UploadFileSerializer, FileUploadSerializer

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
            
            serializer = FileUploadSerializer(data=request.data)
            if serializer.is_valid():
                file = request.FILES['file']
                file_type = serializer.validated_data['file_type']
                
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
                    uploader=request.user
                )
                
                logger.info(f"文件上传成功: {file_url}")
                
                return Response({
                    'code': 200,
                    'data': UploadFileSerializer(upload_file).data,
                    'message': '文件上传成功'
                })
            
            logger.warning(f"数据验证失败: {serializer.errors}")
            return Response({
                'code': 400,
                'message': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': f'文件上传失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
