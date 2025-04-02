from django.db import models

# Create your models here.
class Comment(models.Model):
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已批准'),
        ('rejected', '已拒绝'),
    ]
    
    post = models.ForeignKey('post.Post', on_delete=models.CASCADE, related_name='comments')
    author = models.CharField(max_length=100)
    email = models.EmailField()
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comment'
        ordering = ['-create_time']
        
    def __str__(self):
        return f'Comment by {self.author} on {self.post.title}'
