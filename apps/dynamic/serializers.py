from rest_framework import serializers
from apps.dynamic.models import Dynamic
from apps.user.serializers import UserSerializer
from apps.category.serializers import CategorySerializer
from apps.tag.serializers import TagSerializer


class DynamicSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = Dynamic
        fields = ['id', 'title', 'content', 'author', 'category', 'tags', 
                 'status', 'views', 'create_time', 'update_time']
        read_only_fields = ['author', 'views', 'create_time', 'update_time']


class AdjacentDynamicSerializer(serializers.Serializer):
    prev = DynamicSerializer(required=False)
    next = DynamicSerializer(required=False)


class HotDynamicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dynamic
        fields = ['id', 'title', 'views', 'create_time']


class RecentDynamicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dynamic
        fields = ['id', 'title', 'create_time']