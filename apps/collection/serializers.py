from rest_framework import serializers

from .models import Collection


class CollectionListSerializer(serializers.ModelSerializer):
    itemCount = serializers.IntegerField(source='item_count', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'title', 'description', 'cover', 'series', 'sort', 'status', 'itemCount', 'updatedAt']


class CollectionDetailSerializer(serializers.ModelSerializer):
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'title', 'description', 'cover', 'series', 'status', 'updatedAt']


class CollectionAdminSerializer(serializers.ModelSerializer):
    """后台合集表单/列表：itemCount 与 publishedCount 由 viewset 注解提供。"""

    itemCount = serializers.IntegerField(source='item_count', read_only=True)
    publishedCount = serializers.IntegerField(source='published_count', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Collection
        fields = [
            'id', 'title', 'description', 'cover', 'series', 'sort', 'status',
            'itemCount', 'publishedCount', 'createdAt', 'updatedAt',
        ]
        extra_kwargs = {
            'title': {'required': True, 'allow_blank': False},
            'description': {'required': False, 'allow_blank': True},
            'cover': {'required': False, 'allow_blank': True},
            'series': {'required': False, 'allow_blank': True},
        }
        read_only_fields = ['id', 'createdAt', 'updatedAt']


class CollectionItemAdminSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='dynamic_id')
    title = serializers.CharField(source='dynamic.title')
    status = serializers.CharField(source='dynamic.status')
    createdAt = serializers.DateTimeField(source='dynamic.created_at')
    category = serializers.SerializerMethodField()
    sort = serializers.IntegerField()

    def get_category(self, item):
        category = item.dynamic.category
        return {'id': category.id, 'name': category.name} if category else None
