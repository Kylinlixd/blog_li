from django.db import models
from django.contrib.auth import get_user_model
from apps.category.models import Category
from apps.tag.models import Tag
import json

User = get_user_model()

class Dynamic(models.Model):
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('published', '已发布'),
    )
    
    TYPE_CHOICES = (
        ('text', '文本'),
        ('image', '图片'),
        ('audio', '音频'),
        ('video', '视频'),
    )
    
    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='text', verbose_name='类型')
    images_data = models.TextField(blank=True, null=True, verbose_name='图片数据')
    audio_data = models.TextField(blank=True, null=True, verbose_name='音频数据')
    video_data = models.TextField(blank=True, null=True, verbose_name='视频数据')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='作者')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name='分类')
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='标签')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name='状态')
    views = models.PositiveIntegerField(default=0, verbose_name='浏览量')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '动态'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']

    def __str__(self):
        return self.title
        
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