from django.db import models

# Create your models here.
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="标签名称")
    description = models.TextField(blank=True, null=True)
    sort = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tag'
        ordering = ['-created_at']
        verbose_name = '标签'
        verbose_name_plural = verbose_name
        
    def __str__(self):
        return self.name
