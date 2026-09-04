from rest_framework import serializers
from .models import AccessLog, IpSecurityRule
from .profile import classify_ip
from .rules import normalize_target, validate_rate_window


class AccessLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='')
    ip_type = serializers.SerializerMethodField()

    class Meta:
        model = AccessLog
        fields = ['id', 'ip_address', 'ip_type', 'method', 'path', 'status_code', 'device_type', 'device_model', 'user_agent', 'username', 'created_at']

    def get_ip_type(self, obj):
        return classify_ip(obj.ip_address).get('ip_type', '未知')


class IpSecurityRuleSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default='')
    revoked_by_name = serializers.CharField(source='revoked_by.username', read_only=True, default='')

    class Meta:
        model = IpSecurityRule
        fields = [
            'id', 'target', 'rule_type', 'attack_level', 'requests', 'window_seconds',
            'expires_at', 'is_permanent', 'reason', 'status',
            'created_by', 'created_by_name', 'revoked_by', 'revoked_by_name',
            'created_at', 'updated_at', 'revoked_at',
        ]
        read_only_fields = ['id', 'status', 'created_by', 'revoked_by', 'revoked_at', 'created_at', 'updated_at']

    def validate_target(self, value):
        try:
            return normalize_target(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate(self, attrs):
        validate_rate_window(
            attrs.get('rule_type'),
            attrs.get('requests'),
            attrs.get('window_seconds'),
        )
        if attrs.get('rule_type') == 'ban' and not attrs.get('is_permanent') and not attrs.get('expires_at'):
            raise serializers.ValidationError({'expires_at': '临时封禁必须设置过期时间'})
        return attrs
