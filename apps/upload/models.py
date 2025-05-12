from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class FileCategory(models.Model):
    """文件分类"""
    name = models.CharField(max_length=50, unique=True, help_text="分类名称")
    description = models.TextField(blank=True, help_text="分类描述")
    sort = models.IntegerField(default=0, help_text="排序")
    status = models.BooleanField(default=True, help_text="状态：True-启用，False-禁用")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'file_category'
        ordering = ['sort', '-created_at']
        verbose_name = '文件分类'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

class FileTag(models.Model):
    """文件标签"""
    name = models.CharField(max_length=50, unique=True, help_text="标签名称")
    description = models.TextField(blank=True, help_text="标签描述")
    sort = models.IntegerField(default=0, help_text="排序")
    status = models.BooleanField(default=True, help_text="状态：True-启用，False-禁用")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'file_tag'
        ordering = ['sort', '-created_at']
        verbose_name = '文件标签'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

class UploadFile(models.Model):
    """上传文件"""
    FILE_TYPE_CHOICES = (
        ('image', '图片'),
        ('video', '视频'),
        ('audio', '音频'),
        ('document', '文档'),
        ('other', '其他')
    )

    name = models.CharField(max_length=255, help_text="文件名")
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, help_text="文件类型")
    file_size = models.BigIntegerField(help_text="文件大小(字节)")
    file_url = models.CharField(max_length=500, help_text="文件URL")
    category = models.ForeignKey(FileCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='files')
    tags = models.ManyToManyField(FileTag, blank=True, related_name='files')
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    description = models.TextField(blank=True, help_text="文件描述")
    is_public = models.BooleanField(default=True, help_text="是否公开")
    download_count = models.PositiveIntegerField(default=0, help_text="下载次数")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'upload_file'
        ordering = ['-created_at']
        verbose_name = '上传文件'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def increase_download_count(self):
        """增加下载次数"""
        self.download_count += 1
        self.save(update_fields=['download_count'])
