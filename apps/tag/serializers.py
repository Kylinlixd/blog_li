from rest_framework import serializers
from .models import Tag
from django.db.models import Count

class TagSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    dynamicCount = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'description', 'sort', 'status', 'dynamicCount', 'createdAt', 'updatedAt']
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False},
            'description': {'required': False},
            'sort': {'required': False},
            'status': {'required': False}
        } 
        
    def get_dynamicCount(self, obj):
        # 获取使用该标签的动态数量
        if hasattr(obj, 'dynamic_count'):
            return obj.dynamic_count
        return obj.dynamics.count()

class TagCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name', 'status']
    
    def validate_name(self, value):
        if Tag.objects.filter(name=value).exists():
            raise serializers.ValidationError("标签名称已存在")
        return value

class TagUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name', 'status']
    
    def validate_name(self, value):
        if Tag.objects.filter(name=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("标签名称已存在")
        return value 