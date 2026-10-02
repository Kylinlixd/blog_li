from rest_framework import serializers
from .models import Category

class CategorySerializer(serializers.ModelSerializer):
    dynamic_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'sort', 'status', 'created_at', 'updated_at', 'dynamic_count']
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False},
            'description': {'required': False},
            'sort': {'required': False}
        }
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_dynamic_count(self, obj):
        # 注解优先；retrieve 等未注解的路径回退到实时统计
        if hasattr(obj, 'dynamic_count'):
            return obj.dynamic_count
        return obj.dynamics.filter(status='published').count()


class SimpleCategorySerializer(serializers.ModelSerializer):
    """简化的分类序列化器"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'sort', 'status', 'created_at', 'updated_at']


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'description', 'sort', 'status']
    
    def validate_name(self, value):
        if Category.objects.filter(name=value).exists():
            raise serializers.ValidationError("分类名称已存在")
        return value


class CategoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'description', 'sort', 'status']
    
    def validate_name(self, value):
        if Category.objects.filter(name=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("分类名称已存在")
        return value
