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
