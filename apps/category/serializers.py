from rest_framework import serializers
from .models import Category

class CategorySerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'create_time', 'update_time']
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False},
            'description': {'required': False}
        }