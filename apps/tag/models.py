from django.db import models

# Create your models here.
class Tag(models.Model):
    STATUS_CHOICES = (
        ('active', '启用'),
        ('inactive', '禁用')
    )
    
    name = models.CharField(max_length=50, unique=True, help_text="标签名称")
    description = models.TextField(blank=True, null=True)
    sort = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', help_text="标签状态")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tag'
        ordering = ['-created_at']
        verbose_name = '标签'
        verbose_name_plural = verbose_name
        
    def __str__(self):
        return self.name
