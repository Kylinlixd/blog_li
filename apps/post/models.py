from django.db import models

# Create your models here.
class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布')
    ]
    
    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    summary = models.CharField(max_length=500, blank=True, verbose_name='摘要')
    category = models.ForeignKey('category.Category', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='分类')
    tags = models.ManyToManyField('tag.Tag', blank=True, verbose_name='标签')
    author = models.ForeignKey('user.User', on_delete=models.CASCADE, verbose_name='作者')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='状态')
    views = models.IntegerField(default=0, verbose_name='浏览量')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        ordering = ['-create_time']
        verbose_name = '文章'
        verbose_name_plural = '文章'
        db_table = 'post'

    def __str__(self):
        return self.title