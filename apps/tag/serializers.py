from rest_framework import serializers
from .models import Tag
from django.db.models import Count

class TagSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='create_time', read_only=True)
    updatedAt = serializers.DateTimeField(source='update_time', read_only=True)
    postCount = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'description', 'sort', 'postCount', 'createdAt', 'updatedAt']
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False},
            'description': {'required': False},
            'sort': {'required': False}
        } 
        
    def get_postCount(self, obj):
        # 获取使用该标签的动态数量
        if hasattr(obj, 'dynamic_count'):
            return obj.dynamic_count
        return obj.dynamic_set.count()

class TagCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name']
    
    def validate_name(self, value):
        if Tag.objects.filter(name=value).exists():
            raise serializers.ValidationError("标签名称已存在")
        return value

class TagUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name']
    
    def validate_name(self, value):
        if Tag.objects.filter(name=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("标签名称已存在")
        return value 