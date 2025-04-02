from rest_framework import serializers
from .models import Comment
from apps.post.models import Post

class CommentSerializer(serializers.ModelSerializer):
    postTitle = serializers.CharField(source='post.title', read_only=True)
    postId = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all(), source='post')
    createdAt = serializers.DateTimeField(source='create_time', format="%Y-%m-%d %H:%M:%S", read_only=True)
    updatedAt = serializers.DateTimeField(source='update_time', format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'content', 'postId', 'postTitle', 'author', 'email', 'status', 'createdAt', 'updatedAt']
        read_only_fields = ['createdAt', 'updatedAt'] 