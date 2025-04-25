from rest_framework import serializers
from .models import Category

class CategorySerializer(serializers.ModelSerializer):
    parentId = serializers.PrimaryKeyRelatedField(source='parent', queryset=Category.objects.all(), allow_null=True, required=False)
    createdAt = serializers.DateTimeField(source='create_time', read_only=True)
    updatedAt = serializers.DateTimeField(source='update_time', read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parentId', 'sort', 'children', 'createdAt', 'updatedAt']
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False},
            'description': {'required': False},
            'sort': {'required': False}
        }
    
    def get_children(self, obj):
        # 只为顶级分类获取子分类
        if hasattr(obj, 'children') and obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True).data
        return []
    
    def to_representation(self, instance):
        # 子分类不需要再返回children字段，避免无限嵌套
        ret = super().to_representation(instance)
        if instance.parent is not None:
            ret.pop('children', None)
        return ret


class SimpleCategorySerializer(serializers.ModelSerializer):
    """简化的分类序列化器，不包含子分类"""
    parentId = serializers.PrimaryKeyRelatedField(source='parent', queryset=Category.objects.all(), allow_null=True, required=False)
    createdAt = serializers.DateTimeField(source='create_time', read_only=True)
    updatedAt = serializers.DateTimeField(source='update_time', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parentId', 'sort', 'createdAt', 'updatedAt']