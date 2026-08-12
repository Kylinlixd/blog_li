from rest_framework import serializers
from .models import UploadFile, FileCategory, FileTag
from apps.user.serializers import UserSerializer
from .validation import validate_file_size, validate_file_type

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
        file_type = self.initial_data.get('file_type')
        valid, message = validate_file_type(value, file_type)
        if not valid:
            raise serializers.ValidationError(message)
        valid, message = validate_file_size(value, file_type)
        if not valid:
            raise serializers.ValidationError(message)
        
        return value
