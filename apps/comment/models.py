from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.
class Comment(models.Model):
    STATUS_CHOICES = (
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝')
    )
    
    content = models.TextField(help_text="评论内容")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    dynamic = models.ForeignKey('dynamic.Dynamic', on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comment'
        ordering = ['-created_at']
        verbose_name = '评论'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.author.username}'s comment on {self.dynamic}"
