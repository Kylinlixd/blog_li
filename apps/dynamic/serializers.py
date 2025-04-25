from rest_framework import serializers
from apps.dynamic.models import Dynamic
from apps.user.serializers import UserSerializer
from apps.category.serializers import CategorySerializer
from apps.tag.serializers import TagSerializer
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
    images = serializers.SerializerMethodField()
    audio = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='create_time', read_only=True)
    updatedAt = serializers.DateTimeField(source='update_time', read_only=True)
    
    class Meta:
        model = Dynamic
        fields = ['id', 'title', 'content', 'type', 'author', 'category', 'tags', 
                 'status', 'views', 'images', 'audio', 'video', 
                 'createdAt', 'updatedAt']
        read_only_fields = ['author', 'views', 'create_time', 'update_time']
    
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
    categoryId = serializers.IntegerField(required=False, write_only=True)
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )
    createdAt = serializers.DateTimeField(required=False, write_only=True)
    
    class Meta:
        model = Dynamic
        fields = ['type', 'content', 'status', 'mediaUrls', 'categoryId', 'tags', 'createdAt']
    
    def create(self, validated_data):
        # 获取媒体URL列表并移除，因为它不是模型的直接字段
        media_urls = validated_data.pop('mediaUrls', [])
        # 获取分类ID并移除
        category_id = validated_data.pop('categoryId', None)
        # 获取标签ID列表并移除
        tags_ids = validated_data.pop('tags', [])
        # 如果提供了createdAt，则使用它，否则移除
        created_at = None
        if 'createdAt' in validated_data:
            created_at = validated_data.pop('createdAt')
        
        # 获取请求对象，用于获取当前用户
        request = self.context.get('request')
        
        # 创建动态实例
        instance = Dynamic.objects.create(
            author=request.user,
            **validated_data
        )
        
        # 如果指定了创建时间，则设置
        if created_at:
            instance.create_time = created_at
        
        # 设置分类
        if category_id:
            from apps.category.models import Category
            try:
                category = Category.objects.get(id=category_id)
                instance.category = category
            except Category.DoesNotExist:
                pass
        
        # 设置标签
        if tags_ids:
            from apps.tag.models import Tag
            tags = Tag.objects.filter(id__in=tags_ids)
            instance.tags.set(tags)
        
        # 根据动态类型处理媒体URL
        if media_urls:
            if instance.type == 'image':
                # 将URL列表转换为图片对象列表
                images_data = [{'url': url} for url in media_urls]
                instance.images_data = json.dumps(images_data)
            elif instance.type == 'audio' and media_urls:
                # 只使用第一个URL作为音频URL
                audio_data = {'url': media_urls[0]}
                instance.audio_data = json.dumps(audio_data)
            elif instance.type == 'video' and media_urls:
                # 只使用第一个URL作为视频URL
                video_data = {'url': media_urls[0]}
                instance.video_data = json.dumps(video_data)
        
        instance.save()
        return instance
        
    def update(self, instance, validated_data):
        # 获取媒体URL列表并移除，因为它不是模型的直接字段
        media_urls = validated_data.pop('mediaUrls', None)
        # 获取分类ID并移除
        category_id = validated_data.pop('categoryId', None)
        # 获取标签ID列表并移除
        tags_ids = validated_data.pop('tags', None)
        # 如果提供了createdAt，则使用它，否则移除
        if 'createdAt' in validated_data:
            created_at = validated_data.pop('createdAt')
            instance.create_time = created_at
        
        # 更新实例的其他字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # 设置分类
        if category_id is not None:
            from apps.category.models import Category
            try:
                category = Category.objects.get(id=category_id)
                instance.category = category
            except Category.DoesNotExist:
                # 如果分类不存在，则设置为None
                instance.category = None
        
        # 设置标签
        if tags_ids is not None:
            from apps.tag.models import Tag
            tags = Tag.objects.filter(id__in=tags_ids)
            instance.tags.set(tags)
        
        # 处理媒体URL
        if media_urls is not None:
            if instance.type == 'image':
                # 将URL列表转换为图片对象列表
                images_data = [{'url': url} for url in media_urls]
                instance.images_data = json.dumps(images_data)
            elif instance.type == 'audio' and media_urls:
                # 只使用第一个URL作为音频URL
                audio_data = {'url': media_urls[0]}
                instance.audio_data = json.dumps(audio_data)
            elif instance.type == 'video' and media_urls:
                # 只使用第一个URL作为视频URL
                video_data = {'url': media_urls[0]}
                instance.video_data = json.dumps(video_data)
            elif not media_urls:
                # 如果提供了空列表，则清空媒体数据
                if instance.type == 'image':
                    instance.images_data = None
                elif instance.type == 'audio':
                    instance.audio_data = None
                elif instance.type == 'video':
                    instance.video_data = None
        
        instance.save()
        return instance