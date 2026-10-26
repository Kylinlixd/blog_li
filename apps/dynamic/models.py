from django.db import models
from django.contrib.auth import get_user_model
from apps.category.models import Category
from apps.tag.models import Tag
from apps.upload.models import UploadFile

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
            # 公开列表/搜索的主查询是 status='published' + 按时间倒序，
            # 原有 ['type','status'] 首列用不上，等于没索引。
            models.Index(fields=['status', '-created_at'], name='dynamic_status_created_idx'),
            # 热门列表：status 过滤 + view_count 倒序
            models.Index(fields=['status', '-view_count'], name='dynamic_status_views_idx'),
        ]
    
    def __str__(self):
        return f"{self.author.username}'s {self.type} dynamic"
        
    @property
    def images(self):
        return list(self.media_urls) if self.type == 'image' else []
        
    @property
    def audio(self):
        return self.media_urls[0] if self.type == 'audio' and self.media_urls else None
        
    @property
    def video(self):
        return self.media_urls[0] if self.type == 'video' and self.media_urls else None

class DynamicLike(models.Model):
    dynamic = models.ForeignKey(Dynamic, on_delete=models.CASCADE, related_name='ip_likes')
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('dynamic', 'ip_address')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ip_address} liked {self.dynamic.title}"


class DynamicTranslation(models.Model):
    """文章的机器翻译缓存：一篇文章 × 一种语言只翻译一次，之后直接读库。"""

    LANG_CHOICES = (
        ('en', 'English'),
        ('ja', '日本語'),
        ('ko', '한국어'),
        ('es', 'Español'),
        ('fr', 'Français'),
    )

    dynamic = models.ForeignKey(Dynamic, on_delete=models.CASCADE, related_name='translations')
    lang = models.CharField(max_length=8, choices=LANG_CHOICES)
    title = models.CharField(max_length=400, help_text="翻译后的标题")
    content = models.TextField(help_text="翻译后的正文（保留 Markdown 结构与代码块）")
    provider = models.CharField(max_length=32, blank=True, default='', help_text="翻译来源，便于排查质量")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dynamic_translation'
        ordering = ['lang']
        constraints = [
            models.UniqueConstraint(fields=['dynamic', 'lang'], name='unique_dynamic_translation'),
        ]
        indexes = [
            models.Index(fields=['lang', 'dynamic']),
        ]

    def __str__(self):
        return f"{self.dynamic_id}#{self.lang}"
