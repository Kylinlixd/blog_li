from rest_framework import serializers
from .models import Comment
from apps.dynamic.models import Dynamic
from apps.user.serializers import UserSerializer

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    dynamic = serializers.PrimaryKeyRelatedField(queryset=Dynamic.objects.all())
    createdAt = serializers.DateTimeField(source='create_time', format="%Y-%m-%d %H:%M:%S", read_only=True)
    updatedAt = serializers.DateTimeField(source='update_time', format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'content', 'user', 'dynamic', 'create_time', 'updatedAt']
        read_only_fields = ['user', 'create_time', 'updatedAt'] 