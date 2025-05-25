from rest_framework import serializers
from .models import Category

class CategorySerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    dynamicCount = serializers.IntegerField(source='dynamic_count', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'sort', 'createdAt', 'updatedAt', 'dynamicCount']
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False},
            'description': {'required': False},
            'sort': {'required': False}
        }
        read_only_fields = ['id', 'createdAt', 'updatedAt']


class SimpleCategorySerializer(serializers.ModelSerializer):
    """简化的分类序列化器"""
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'sort', 'createdAt', 'updatedAt']


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'description', 'sort']
    
    def validate_name(self, value):
        if Category.objects.filter(name=value).exists():
            raise serializers.ValidationError("分类名称已存在")
        return value


class CategoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'description', 'sort']
    
    def validate_name(self, value):
        if Category.objects.filter(name=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("分类名称已存在")
        return value