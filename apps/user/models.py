from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    nickname = models.CharField(max_length=50, blank=True)
    avatar = models.URLField(blank=True)
    bio = models.TextField(blank=True, help_text="用户个人简介")
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, default='user')
    permissions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username