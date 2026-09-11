from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('comment', '0003_comment_email_comment_nickname'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='website',
            field=models.URLField(blank=True, default='', help_text='评论者网址', max_length=500),
        ),
    ]
