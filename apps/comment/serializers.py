import re

from rest_framework import serializers
from .models import Comment
from apps.dynamic.models import Dynamic
from apps.user.models import User
from blog.request_utils import is_public_blog_request


REJECTED_CONTENT_TERMS = (
    '杀人', '杀你', '砍死', '枪杀', '炸死', '血洗', '肢解', '虐杀',
    '强奸', '轮奸', '色情', '淫秽', '裸体', '裸聊', '黄片', '约炮',
    '操你妈', '操你媽', '操你母', '草泥马', '草泥馬', '你妈的', '你媽的',
    '妈的', '媽的', 'cnm', 'nmsl', 'fuck', 'motherfucker', 'porn', 'sex video',
)

REVIEW_CONTENT_TERMS = (
    '傻逼', '笨蛋', '白痴', '混蛋', '王八蛋', '狗屎', '垃圾', '废物', '蠢货', '贱人',
)

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
            return obj.author.avatar
        return '/default-avatar.png'
    
    def get_content(self, obj):
        # 只有待审核状态的评论才添加审核中标记
        if obj.status == 'pending':
            return f"{obj.content}（审核中）"  # 使用中文括号，更美观
        # 已通过或已拒绝的评论直接返回原内容
        return obj.content


class PublicCommentSerializer(CommentSerializer):
    class Meta(CommentSerializer.Meta):
        fields = [
            'id', 'dynamic_id', 'content', 'nickname',
            'avatar', 'createTime', 'status'
        ]

class CommentCreateSerializer(serializers.ModelSerializer):
    dynamic_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Comment
        fields = ['content', 'dynamic_id', 'nickname', 'email']
        extra_kwargs = {
            'content': {'max_length': 2000, 'allow_blank': False, 'trim_whitespace': True},
            'nickname': {'max_length': 50, 'allow_blank': True},
            'email': {'max_length': 254, 'allow_blank': True},
        }

    def validate_content(self, value):
        if is_public_blog_request(self.context['request']):
            normalized = re.sub(r'[\W_]+', '', value.casefold(), flags=re.UNICODE)
            if any(re.sub(r'[\W_]+', '', term.casefold(), flags=re.UNICODE) in normalized for term in REJECTED_CONTENT_TERMS):
                raise serializers.ValidationError('评论包含暴力、涉黄或其他违规内容，请规范言辞后重试。')
        return value
    
    def create(self, validated_data):
        # 如果是前台请求，使用默认用户（游客）
        if is_public_blog_request(self.context['request']):
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
            contains_sensitive = any(word in content for word in REVIEW_CONTENT_TERMS)
            
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
