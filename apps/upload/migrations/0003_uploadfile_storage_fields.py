from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("upload", "0002_filecategory_filetag_uploadfile_description_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadfile",
            name="storage_backend",
            field=models.CharField(
                choices=[("local", "本地存储"), ("xion", "AstraStoreXion")],
                default="local",
                help_text="文件字节所在的存储后端",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="uploadfile",
            name="storage_key",
            field=models.CharField(
                blank=True,
                help_text="存储后端中的对象标识；历史本地记录可为空",
                max_length=500,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="uploadfile",
            name="checksum",
            field=models.CharField(blank=True, help_text="SHA-256校验和", max_length=64),
        ),
        migrations.AddField(
            model_name="uploadfile",
            name="content_type",
            field=models.CharField(blank=True, help_text="文件MIME类型", max_length=255),
        ),
    ]
