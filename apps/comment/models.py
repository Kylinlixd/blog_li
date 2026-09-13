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
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', default=1)
    dynamic = models.ForeignKey('dynamic.Dynamic', on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    nickname = models.CharField(max_length=50, blank=True, help_text="评论者昵称")
    email = models.EmailField(blank=True, help_text="评论者邮箱")
    website = models.URLField(max_length=500, blank=True, default='', help_text="评论者网址")
    client_os = models.CharField(max_length=50, blank=True, default='', help_text="评论者操作系统")
    client_browser = models.CharField(max_length=50, blank=True, default='', help_text="评论者浏览器")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comment'
        ordering = ['-created_at']
        verbose_name = '评论'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.nickname or self.author.username}'s comment on {self.dynamic}"


class CommentReadState(models.Model):
    """Monotonic per-admin cursor for comments visible to that account."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='comment_read_state')
    last_seen_comment_id = models.PositiveBigIntegerField(default=0)
    initialized_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'comment_read_state'

class CommentReadReceipt(models.Model):
    """Per-admin read marker; absence means the comment is unread."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_read_receipts')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='read_receipts')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'comment_read_receipt'
        constraints = [
            models.UniqueConstraint(fields=['user', 'comment'], name='unique_comment_read_receipt'),
        ]
