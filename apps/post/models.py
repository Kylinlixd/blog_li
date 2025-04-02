from django.db import models

# Create your models here.
class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布')
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    summary = models.CharField(max_length=500)
    category = models.ForeignKey('category.Category', on_delete=models.SET_NULL, null=True)
    tags = models.ManyToManyField('tag.Tag')
    author = models.ForeignKey('user.User', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    views = models.PositiveIntegerField(default=0)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'post'