from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    nickname = models.CharField(max_length=50, blank=True)
    avatar = models.URLField(blank=True)
    
    class Meta:
        db_table = 'user'