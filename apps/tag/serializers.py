from rest_framework import serializers
from .models import Tag

class TagSerializer(serializers.ModelSerializer):
    createTime = serializers.DateTimeField(source='create_time', format="%Y-%m-%d %H:%M:%S", read_only=True)
    updateTime = serializers.DateTimeField(source='update_time', format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'createTime', 'updateTime']
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False}
        } 