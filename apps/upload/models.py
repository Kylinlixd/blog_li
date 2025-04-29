from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UploadFile(models.Model):
    FILE_TYPE_CHOICES = (
        ('image', '图片'),
        ('video', '视频'),
        ('document', '文档'),
        ('other', '其他')
    )
    
    name = models.CharField(max_length=255, help_text="文件名")
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, help_text="文件类型")
    file_size = models.IntegerField(help_text="文件大小(字节)")
    file_url = models.URLField(max_length=500, help_text="文件URL")
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'upload_file'
        ordering = ['-created_at']
        verbose_name = '上传文件'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.name
