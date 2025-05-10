from rest_framework import serializers
from .models import Dynamic
from apps.user.serializers import UserSerializer
from apps.category.serializers import CategorySerializer
from apps.tag.serializers import TagSerializer
from apps.upload.serializers import UploadFileSerializer
import json


class ImageSerializer(serializers.Serializer):
    url = serializers.CharField()
    width = serializers.IntegerField(required=False)
    height = serializers.IntegerField(required=False)


class AudioSerializer(serializers.Serializer):
    url = serializers.CharField()
    duration = serializers.IntegerField(required=False)


class VideoSerializer(serializers.Serializer):
    url = serializers.CharField()
    cover = serializers.CharField(required=False)
    duration = serializers.IntegerField(required=False)


class DynamicSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    files = UploadFileSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    
    class Meta:
        model = Dynamic
        fields = [
            'id', 'content', 'type', 'status', 'media_urls',
            'category', 'tags', 'view_count', 'createdAt', 'updatedAt',
            'author', 'files'
        ]
        read_only_fields = ['id', 'author', 'view_count', 'created_at', 'updated_at']
    
    def get_images(self, obj):
        if obj.type != 'image' or not obj.images_data:
            return []
        return obj.images
    
    def get_audio(self, obj):
        if obj.type != 'audio' or not obj.audio_data:
            return None
        return obj.audio
    
    def get_video(self, obj):
        if obj.type != 'video' or not obj.video_data:
            return None
        return obj.video
    
    def create(self, validated_data):
        request = self.context.get('request')
        images = request.data.get('images', [])
        audio = request.data.get('audio', None)
        video = request.data.get('video', None)
        
        instance = Dynamic.objects.create(
            author=request.user,
            **validated_data
        )
        
        if images and instance.type == 'image':
            instance.images_data = json.dumps(images)
        
        if audio and instance.type == 'audio':
            instance.audio_data = json.dumps(audio)
        
        if video and instance.type == 'video':
            instance.video_data = json.dumps(video)
        
        instance.save()
        return instance
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        images = request.data.get('images', None)
        audio = request.data.get('audio', None)
        video = request.data.get('video', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if images is not None and instance.type == 'image':
            instance.images_data = json.dumps(images)
        
        if audio is not None and instance.type == 'audio':
            instance.audio_data = json.dumps(audio)
        
        if video is not None and instance.type == 'video':
            instance.video_data = json.dumps(video)
        
        instance.save()
        return instance


class AdjacentDynamicSerializer(serializers.Serializer):
    prev = DynamicSerializer(required=False)
    next = DynamicSerializer(required=False)


class HotDynamicSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='create_time', read_only=True)
    
    class Meta:
        model = Dynamic
        fields = ['id', 'title', 'views', 'createdAt']


class RecentDynamicSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='create_time', read_only=True)
    
    class Meta:
        model = Dynamic
        fields = ['id', 'title', 'createdAt']


class AdminDynamicSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    audio = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='create_time', read_only=True)
    updatedAt = serializers.DateTimeField(source='update_time', read_only=True)
    
    class Meta:
        model = Dynamic
        fields = ['id', 'content', 'type', 'status', 'createdAt', 'updatedAt',
                 'images', 'audio', 'video']
    
    def get_images(self, obj):
        if obj.type != 'image' or not obj.images_data:
            return []
        return obj.images
    
    def get_audio(self, obj):
        if obj.type != 'audio' or not obj.audio_data:
            return None
        return obj.audio
    
    def get_video(self, obj):
        if obj.type != 'video' or not obj.video_data:
            return None
        return obj.video


class SimpleDynamicSerializer(serializers.ModelSerializer):
    """
    简化的动态序列化器，按照指定格式返回动态数据
    {
      "type": "text/image/audio/video", // 内容类型
      "content": "动态的文字内容", // 文本内容
      "mediaUrls": [], // 媒体文件URL数组，根据类型包含图片、音频或视频链接
      "status": "draft/published" // 状态：草稿或已发布
    }
    """
    mediaUrls = serializers.SerializerMethodField()
    
    class Meta:
        model = Dynamic
        fields = ['id', 'type', 'content', 'mediaUrls', 'status']
    
    def get_mediaUrls(self, obj):
        # 根据动态类型返回不同的媒体URL
        if obj.type == 'image' and obj.images_data:
            # 从图片数据中提取所有URL
            return [img.get('url') for img in obj.images]
        elif obj.type == 'audio' and obj.audio_data:
            # 返回音频URL
            audio = obj.audio
            return [audio.get('url')] if audio and 'url' in audio else []
        elif obj.type == 'video' and obj.video_data:
            # 返回视频URL
            video = obj.video
            return [video.get('url')] if video and 'url' in video else []
        else:
            return []


class DynamicCreateSerializer(serializers.ModelSerializer):
    """
    接收前端发送的动态创建数据
    {
      "type": "text/image/audio/video",
      "content": "动态内容",
      "status": "draft/published",
      "mediaUrls": ["url1", "url2", ...],
      "fileIds": [1, 2, 3],  // 文件ID数组
      "categoryId": 1,  // 分类ID
      "tags": [1, 2, 3], // 标签ID数组
      "author": "作者信息",
      "createdAt": "2023-10-30T12:34:56.789Z"
    }
    """
    mediaUrls = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True
    )
    fileIds = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )
    categoryId = serializers.IntegerField(required=False, write_only=True)
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )
    createdAt = serializers.DateTimeField(required=False, write_only=True)
    
    class Meta:
        model = Dynamic
        fields = ['content', 'type', 'status', 'media_urls', 'category', 'tags', 
                 'categoryId', 'mediaUrls', 'fileIds', 'createdAt']
    
    def create(self, validated_data):
        # 提取特殊字段
        media_urls = validated_data.pop('mediaUrls', [])
        file_ids = validated_data.pop('fileIds', [])
        category_id = validated_data.pop('categoryId', None)
        tags = validated_data.pop('tags', [])
        created_at = validated_data.pop('createdAt', None)
        
        # 创建动态实例
        instance = Dynamic.objects.create(
            author=self.context['request'].user,
            media_urls=media_urls,
            category_id=category_id,
            **validated_data
        )
        
        # 添加文件关联
        if file_ids:
            instance.files.set(file_ids)
        
        # 添加标签
        if tags:
            instance.tags.set(tags)
            
        # 设置创建时间（如果提供）
        if created_at:
            instance.created_at = created_at
            instance.save()
            
        return instance


class DynamicUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dynamic
        fields = ['content', 'type', 'status', 'media_urls', 'category', 'tags']


class DynamicListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    
    class Meta:
        model = Dynamic
        fields = [
            'id', 'content', 'type', 'status', 'media_urls',
            'category', 'tags', 'view_count', 'createdAt', 'updatedAt',
            'author'
        ]