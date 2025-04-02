from rest_framework import serializers
from .models import Category

class CategorySerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='create_time', format="%Y-%m-%d %H:%M:%S", read_only=True)
    updatedAt = serializers.DateTimeField(source='update_time', format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'createdAt', 'updatedAt']
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False},
            'description': {'required': False}
        }