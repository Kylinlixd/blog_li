from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.
class Comment(models.Model):
    content = models.TextField(verbose_name='评论内容')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='评论用户')
    dynamic = models.ForeignKey('dynamic.Dynamic', on_delete=models.CASCADE, verbose_name='评论动态')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '评论'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.user.username} 评论了 {self.dynamic.title}'
