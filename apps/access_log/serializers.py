from rest_framework import serializers
from .models import AccessLog


class AccessLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='')

    class Meta:
        model = AccessLog
        fields = ['id', 'ip_address', 'method', 'path', 'status_code', 'device_type', 'device_model', 'user_agent', 'username', 'created_at']
