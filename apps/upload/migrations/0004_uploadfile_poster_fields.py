from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("upload", "0003_uploadfile_storage_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadfile",
            name="poster_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="视频封面URL",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="uploadfile",
            name="poster_storage_backend",
            field=models.CharField(
                blank=True,
                default="",
                help_text="封面存储后端",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="uploadfile",
            name="poster_storage_key",
            field=models.CharField(
                blank=True,
                default="",
                help_text="封面存储标识",
                max_length=500,
            ),
        ),
    ]
