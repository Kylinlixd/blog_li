from rest_framework import serializers
from apps.tag.models import Tag
from apps.post.models import Post

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class PostSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source='tags',
        many=True,
        write_only=True
    )
    
    class Meta:
        model = Post
        fields = '__all__'
        read_only_fields = ['author', 'create_time', 'update_time']