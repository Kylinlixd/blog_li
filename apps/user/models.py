from django.db import models
from django.contrib.auth.models import AbstractUser, Permission
from django.utils import timezone
from datetime import timedelta

# Create your models here.
class User(AbstractUser):
    nickname = models.CharField(max_length=50, blank=True)
    avatar = models.URLField(blank=True)
    bio = models.TextField(blank=True, help_text="用户个人简介")
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, default='user')
    permissions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username

# Token黑名单模型
class TokenBlacklist(models.Model):
    """
    JWT令牌黑名单，用于使令牌失效
    """
    token = models.CharField(max_length=500, unique=True, verbose_name='Token')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    expires_at = models.DateTimeField(verbose_name='过期时间')
    
    class Meta:
        verbose_name = 'Token黑名单'
        verbose_name_plural = 'Token黑名单'
        
    def __str__(self):
        return f"{self.token[:20]}... ({self.created_at})"
    
    @classmethod
    def add_token_to_blacklist(cls, token, expires_delta=None):
        """
        将token添加到黑名单
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=15)  # 默认15分钟
            
        expires_at = timezone.now() + expires_delta
        
        return cls.objects.create(
            token=token,
            expires_at=expires_at
        )
    
    @classmethod
    def is_blacklisted(cls, token):
        """
        检查token是否在黑名单中
        """
        return cls.objects.filter(token=token).exists()
    
    @classmethod
    def clean_expired_tokens(cls):
        """
        清理过期的token
        """
        now = timezone.now()
        return cls.objects.filter(expires_at__lt=now).delete()