from rest_framework import serializers
from apps.user.models import User

class UserSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='date_joined', format="%Y-%m-%d %H:%M:%S", read_only=True)
    updatedAt = serializers.DateTimeField(source='last_login', format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'email', 'bio', 'avatar', 'createdAt', 'updatedAt']

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class ChangePasswordSerializer(serializers.Serializer):
    oldPassword = serializers.CharField()
    newPassword = serializers.CharField()

class RegisterSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['username', 'password', 'nickname']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        nickname = validated_data.get('nickname', '')
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            nickname=nickname
        )
        return user

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['nickname', 'email', 'bio', 'avatar']
        extra_kwargs = {
            'nickname': {'required': False, 'allow_blank': True},
            'email': {'required': False, 'allow_blank': True},
            'bio': {'required': False, 'allow_blank': True},
            'avatar': {'required': False, 'allow_blank': True},
        }