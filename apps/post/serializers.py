from rest_framework import serializers
from apps.post.models import Post
from apps.category.models import Category
from apps.tag.models import Tag
from django.contrib.auth import get_user_model

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class PostListSerializer(serializers.ModelSerializer):
    tagIds = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),required=False # 允许的标签查询集
    )
    tags = TagSerializer(many=True, read_only=True)
    categoryName = serializers.CharField(source='category.name', read_only=True)
    createTime = serializers.DateTimeField(source='create_time', format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    updateTime = serializers.DateTimeField(source='update_time', format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    categoryId = serializers.IntegerField(source='category.id', read_only=True)
    viewCount = serializers.IntegerField(source='views', read_only=True)
    authorId = serializers.IntegerField(source='author.id', read_only=True)
    content = serializers.CharField()
    status = serializers.CharField()

    class Meta:
        model = Post
        fields = ['id', 'title', 'summary', 'createTime', 'updateTime', 
                 'categoryId', 'categoryName', 'viewCount', 'tagIds', 'tags', 'authorId', 'content', 'status']

class PostDetailSerializer(serializers.ModelSerializer):
    tagIds = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(), required=False # 允许的标签查询集
    )
    tags = TagSerializer(many=True, read_only=True)
    categoryName = serializers.CharField(source='category.name', read_only=True)
    createTime = serializers.DateTimeField(source='create_time', format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    updateTime = serializers.DateTimeField(source='update_time', format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    categoryId = serializers.IntegerField(source='category.id', read_only=True)
    viewCount = serializers.IntegerField(source='views', read_only=True)
    content = serializers.CharField()
    status = serializers.CharField()
    
    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'summary', 'createTime', 'updateTime', 
                 'categoryId', 'categoryName', 'viewCount', 'tagIds', 'tags', 'content', 'status']

class AdjacentPostSerializer(serializers.Serializer):
    prev = serializers.SerializerMethodField()
    next = serializers.SerializerMethodField()
    
    def get_prev(self, obj):
        if obj['prev']:
            return {
                'id': obj['prev'].id,
                'title': obj['prev'].title
            }
        return None
    
    def get_next(self, obj):
        if obj['next']:
            return {
                'id': obj['next'].id,
                'title': obj['next'].title
            }
        return None

class HotPostSerializer(serializers.ModelSerializer):
    createTime = serializers.DateTimeField(source='create_time', format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    viewCount = serializers.IntegerField(source='views', read_only=True)
    
    class Meta:
        model = Post
        fields = ['id', 'title', 'viewCount', 'createTime']

class RecentPostSerializer(serializers.ModelSerializer):
    createTime = serializers.DateTimeField(source='create_time', format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    
    class Meta:
        model = Post
        fields = ['id', 'title', 'createTime']

class PostSerializer(serializers.ModelSerializer):
    categoryId = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    tagIds = serializers.PrimaryKeyRelatedField(
        source='tags',
        many=True,
        queryset=Tag.objects.all(),
        required=False
    )
    authorId = serializers.PrimaryKeyRelatedField(
        source='author',
        queryset=get_user_model().objects.all(),
        required=False
    )
    createTime = serializers.DateTimeField(source='create_time', format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    updateTime = serializers.DateTimeField(source='update_time', format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    viewCount = serializers.IntegerField(source='views', read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'content', 'summary', 
            'categoryId', 'tagIds', 'status', 'authorId',
            'viewCount', 'createTime', 'updateTime'
        ]
        read_only_fields = ['viewCount', 'createTime', 'updateTime']

    def to_representation(self, instance):
        """修改序列化输出格式"""
        ret = super().to_representation(instance)
        # 确保categoryId为null时返回null
        if ret['categoryId'] is None:
            ret['categoryId'] = None
        # 确保tagIds为列表
        if ret['tagIds'] is None:
            ret['tagIds'] = []
        return ret

    def create(self, validated_data):
        # 处理标签
        tags = validated_data.pop('tags', [])
        post = super().create(validated_data)
        post.tags.set(tags)
        return post

    def update(self, instance, validated_data):
        # 处理标签
        tags = validated_data.pop('tags', [])
        post = super().update(instance, validated_data)
        post.tags.set(tags)
        return post