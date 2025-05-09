from django.db import models

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="分类名称")
    description = models.TextField(blank=True, help_text="分类描述")
    sort = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'category'
        ordering = ['sort', 'id']
        verbose_name = '分类'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name