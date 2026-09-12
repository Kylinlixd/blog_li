from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('comment', '0004_comment_website'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='client_os',
            field=models.CharField(blank=True, default='', help_text='评论者操作系统', max_length=50),
        ),
        migrations.AddField(
            model_name='comment',
            name='client_browser',
            field=models.CharField(blank=True, default='', help_text='评论者浏览器', max_length=50),
        ),
    ]
