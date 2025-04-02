from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    nickname = models.CharField(max_length=50, blank=True)
    avatar = models.URLField(blank=True)
    bio = models.TextField(blank=True, help_text="用户个人简介")
    
    class Meta:
        db_table = 'user'