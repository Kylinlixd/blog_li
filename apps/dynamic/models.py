from django.db import models
from django.contrib.auth import get_user_model
from apps.category.models import Category
from apps.tag.models import Tag
from apps.upload.models import UploadFile
import json

User = get_user_model()

class Dynamic(models.Model):
    TYPE_CHOICES = (
        ('text', '文本'),
        ('image', '图片'),
        ('audio', '音频'),
        ('video', '视频')
    )
    
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('published', '已发布')
    )
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dynamics')
    title = models.CharField(max_length=200, help_text="动态标题")
    content = models.TextField(help_text="动态内容")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='text')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    media_urls = models.JSONField(default=list, blank=True, help_text="媒体文件URL数组")
    files = models.ManyToManyField(UploadFile, related_name='dynamics', blank=True, help_text="关联的文件")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='dynamics')
    tags = models.ManyToManyField(Tag, related_name='dynamics', blank=True)
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    liked_by = models.ManyToManyField(User, related_name='liked_dynamics', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'dynamic'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['type', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.author.username}'s {self.type} dynamic"
        
    @property
    def images(self):
        if self.images_data:
            return json.loads(self.images_data)
        return []
        
    @property
    def audio(self):
        if self.audio_data:
            return json.loads(self.audio_data)
        return None
        
    @property
    def video(self):
        if self.video_data:
            return json.loads(self.video_data)
        return None

class DynamicLike(models.Model):
    dynamic = models.ForeignKey(Dynamic, on_delete=models.CASCADE, related_name='ip_likes')
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('dynamic', 'ip_address')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ip_address} liked {self.dynamic.title}"