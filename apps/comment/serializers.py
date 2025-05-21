from rest_framework import serializers
from .models import Comment
from apps.dynamic.models import Dynamic
from apps.user.serializers import UserSerializer
from apps.user.models import User  # 使用自定义用户模型

class CommentSerializer(serializers.ModelSerializer):
    dynamic_id = serializers.IntegerField(source='dynamic.id')
    createTime = serializers.DateTimeField(source='created_at')
    avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'dynamic_id', 'content', 'nickname',
            'email', 'avatar', 'createTime', 'status'
        ]
    
    def get_avatar(self, obj):
        if obj.author and obj.author.avatar:
            return obj.author.avatar.url
        return '/default-avatar.png'

class CommentCreateSerializer(serializers.ModelSerializer):
    dynamic_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Comment
        fields = ['content', 'dynamic_id', 'nickname', 'email']
    
    def create(self, validated_data):
        # 如果是前台请求，使用默认用户（游客）
        if self.context['request'].path.startswith('/blog'):
            try:
                # 尝试获取默认用户，如果不存在则创建
                default_user, created = User.objects.get_or_create(
                    id=1,
                    defaults={
                        'username': 'guest',
                        'email': 'guest@example.com',
                        'is_active': True
                    }
                )
                validated_data['author'] = default_user
            except Exception as e:
                print(f"创建默认用户时出错: {str(e)}")
                raise serializers.ValidationError({'author': '无法创建默认用户'})
            
            # 获取动态 ID
            dynamic_id = validated_data.pop('dynamic_id')
            try:
                validated_data['dynamic'] = Dynamic.objects.get(id=dynamic_id)
            except Dynamic.DoesNotExist:
                raise serializers.ValidationError({'dynamic_id': '动态不存在'})
            # 设置默认状态为待审核
            validated_data['status'] = 'pending'
        else:
            validated_data['author'] = self.context['request'].user
        return super().create(validated_data)

class CommentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['content', 'status', 'nickname', 'email']
    
    def validate_status(self, value):
        if value not in ['pending', 'approved', 'rejected']:
            raise serializers.ValidationError("无效的状态值")
        return value 