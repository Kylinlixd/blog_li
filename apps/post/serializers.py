from rest_framework import serializers
from apps.tag.models import Tag
from apps.post.models import Post
from apps.category.models import Category

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