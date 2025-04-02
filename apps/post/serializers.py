from rest_framework import serializers
from apps.tag.models import Tag
from apps.post.models import Post
from apps.category.models import Category

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class PostSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tagIds = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source='tags',
        many=True,
        write_only=True
    )
    categoryId = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category'
    )
    categoryName = serializers.CharField(source='category.name', read_only=True)
    createTime = serializers.DateTimeField(source='create_time', format="%Y-%m-%d %H:%M:%S", read_only=True)
    updateTime = serializers.DateTimeField(source='update_time', format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'summary', 'categoryId', 'categoryName', 
                  'tags', 'tagIds', 'status', 'createTime', 'updateTime']
        read_only_fields = ['author', 'createTime', 'updateTime']