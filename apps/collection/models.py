from django.db import models


class Collection(models.Model):
    """文章合集（专栏）：按系列组织的有序阅读路径，发布器自动维护。"""

    STATUS_CHOICES = (
        ('active', '启用'),
        ('hidden', '隐藏'),
    )

    title = models.CharField(max_length=100, unique=True, help_text="合集标题")
    description = models.TextField(blank=True, help_text="合集简介")
    cover = models.CharField(max_length=500, blank=True, help_text="封面图 URL")
    series = models.CharField(max_length=50, blank=True, help_text="关联的系列名（发布器自动维护用）")
    sort = models.IntegerField(default=0, help_text="排序")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'collection'
        ordering = ['sort', 'id']
        verbose_name = '合集'
        verbose_name_plural = '合集'

    def __str__(self):
        return self.title


class CollectionItem(models.Model):
    """合集条目：文章在合集内的章节顺序。"""

    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='items')
    dynamic = models.ForeignKey('dynamic.Dynamic', on_delete=models.CASCADE, related_name='collection_items')
    sort = models.IntegerField(default=0, help_text="章节序号")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'collection_item'
        ordering = ['sort', 'id']
        unique_together = ('collection', 'dynamic')
        verbose_name = '合集条目'
        verbose_name_plural = '合集条目'

    def __str__(self):
        return f'{self.collection.title} #{self.sort} {self.dynamic.title}'
