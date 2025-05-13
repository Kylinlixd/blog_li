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
            'uploader', 'description', 'is_public', 'download_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'file_url', 'file_size', 'download_count', 'created_at', 'updated_at']

class FileListSerializer(serializers.Serializer):
    items = UploadFileSerializer(many=True)
    total = serializers.IntegerField()
    
    class Meta:
        fields = ['items', 'total']

class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    file_type = serializers.ChoiceField(choices=UploadFile.FILE_TYPE_CHOICES, required=True)
    
    def validate_file(self, value):
        # 验证文件大小（限制为10MB）
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("文件大小不能超过10MB")
        
        # 验证文件类型
        allowed_types = {
            'image': ['image/jpeg', 'image/png', 'image/gif'],
            'video': ['video/mp4', 'video/quicktime'],
            'document': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        }
        
        file_type = self.initial_data.get('file_type')
        if file_type in allowed_types and value.content_type not in allowed_types[file_type]:
            raise serializers.ValidationError(f"不支持的文件类型，请上传{file_type}类型的文件")
        
        return value 