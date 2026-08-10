from django.conf import settings
import os

from rest_framework import serializers
from .models import UploadFile, FileCategory, FileTag
from apps.user.serializers import UserSerializer

class FileCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FileCategory
        fields = ['id', 'name', 'description', 'sort', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class FileTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileTag
        fields = ['id', 'name', 'description', 'sort', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class UploadFileSerializer(serializers.ModelSerializer):
    uploader = UserSerializer(read_only=True)
    
    class Meta:
        model = UploadFile
        fields = [
            'id', 'name', 'file_type', 'file_size', 'file_url',
            'storage_backend', 'checksum', 'content_type',
            'poster_url', 'poster_storage_backend', 'poster_storage_key',
            'uploader', 'description', 'is_public', 'download_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_url', 'file_size', 'storage_backend',
            'checksum', 'content_type', 'download_count', 'created_at', 'updated_at',
            'poster_url', 'poster_storage_backend', 'poster_storage_key',
        ]

class FileListSerializer(serializers.Serializer):
    items = UploadFileSerializer(many=True)
    total = serializers.IntegerField()
    
    class Meta:
        fields = ['items', 'total']

class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    file_type = serializers.ChoiceField(choices=UploadFile.FILE_TYPE_CHOICES, required=True)
    
    def validate_file(self, value):
        # 与上传视图保持同一套公开大小限制，避免入口之间出现冲突。
        max_size = settings.BLOG_FILE_MAX_UPLOAD_BYTES
        if value.size > max_size:
            raise serializers.ValidationError(f"文件大小不能超过{max_size / 1024 / 1024}MB")
        
        # 验证文件类型
        allowed_types = {
            'image': ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/heic', 'image/heif'],
            'video': ['video/mp4', 'video/quicktime', 'video/x-m4v', 'video/webm', 'video/hevc'],
            'document': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        }
        
        file_type = self.initial_data.get('file_type')
        if file_type in allowed_types and value.content_type not in allowed_types[file_type]:
            raise serializers.ValidationError(f"不支持的文件类型，请上传{file_type}类型的文件")

        allowed_extensions = {
            'image': {'jpg', 'jpeg', 'png', 'gif', 'heic', 'heif'},
            'video': {'mp4', 'mov', 'm4v', 'avi', 'webm', 'hevc'},
            'document': {'pdf', 'doc', 'docx', 'xls', 'xlsx'},
        }
        extension = os.path.splitext(value.name)[1].lower().lstrip('.')
        if file_type in allowed_extensions and extension not in allowed_extensions[file_type]:
            raise serializers.ValidationError(f"不支持的文件扩展名，请上传{file_type}类型的文件")
        
        return value
