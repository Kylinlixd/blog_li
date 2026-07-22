from rest_framework import serializers
from .models import Comment
from apps.dynamic.models import Dynamic
from apps.user.models import User

class CommentSerializer(serializers.ModelSerializer):
    dynamic_id = serializers.IntegerField(source='dynamic.id')
    createTime = serializers.DateTimeField(source='created_at')
    avatar = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    
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
    
    def get_content(self, obj):
        # 只有待审核状态的评论才添加审核中标记
        if obj.status == 'pending':
            return f"{obj.content}（审核中）"  # 使用中文括号，更美观
        # 已通过或已拒绝的评论直接返回原内容
        return obj.content

class CommentCreateSerializer(serializers.ModelSerializer):
    dynamic_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Comment
        fields = ['content', 'dynamic_id', 'nickname', 'email']
    
    def create(self, validated_data):
        # 如果是前台请求，使用默认用户（游客）
        if self.context['request'].path.startswith('/blog'):
            dynamic_id = validated_data.pop('dynamic_id')
            try:
                validated_data['dynamic'] = Dynamic.objects.get(
                    id=dynamic_id,
                    status='published'
                )
            except Dynamic.DoesNotExist:
                raise serializers.ValidationError({'dynamic_id': '公开内容不存在'})

            default_user, _ = User.objects.get_or_create(
                username='guest',
                defaults={
                    'email': 'guest@example.com',
                    'is_active': False,
                    'role': 'guest'
                }
            )
            validated_data['author'] = default_user
            
            # 自动审核逻辑
            content = validated_data.get('content', '')
            # 检查评论内容是否包含敏感词
            sensitive_words = ['傻逼', '笨蛋', '白痴', '混蛋', '王八蛋', '狗屎', '垃圾', '废物', '蠢货', '贱人']
            contains_sensitive = any(word in content for word in sensitive_words)
            
            if contains_sensitive:
                validated_data['status'] = 'pending'  # 包含敏感词，需要人工审核
            else:
                validated_data['status'] = 'approved'  # 不包含敏感词，自动通过
        else:
            validated_data['author'] = self.context['request'].user
            validated_data['status'] = 'pending'  # 后台创建的评论默认待审核
        
        return super().create(validated_data)

class CommentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['content', 'status', 'nickname', 'email']
    
    def validate_status(self, value):
        if value not in ['pending', 'approved', 'rejected']:
            raise serializers.ValidationError("无效的状态值")
        return value
