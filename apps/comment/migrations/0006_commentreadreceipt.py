from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def initialize_existing_comments_as_read(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    Comment = apps.get_model('comment', 'Comment')
    Receipt = apps.get_model('comment', 'CommentReadReceipt')
    boundary = timezone.now()
    users = User.objects.filter(role__in=['admin', 'editor', 'moderator']) | User.objects.filter(is_staff=True)
    comments = list(Comment.objects.filter(created_at__lte=boundary).values_list('id', flat=True))
    for user in users.distinct().iterator():
        Receipt.objects.bulk_create(
            [Receipt(user_id=user.pk, comment_id=comment_id, read_at=boundary) for comment_id in comments],
            ignore_conflicts=True,
            batch_size=500,
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('user', '0002_alter_user_options_user_created_at_user_permissions_and_more'),
        ('comment', '0005_comment_client_metadata'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommentReadReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='read_receipts', to='comment.comment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comment_read_receipts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'comment_read_receipt'},
        ),
        migrations.AddConstraint(
            model_name='commentreadreceipt',
            constraint=models.UniqueConstraint(fields=('user', 'comment'), name='unique_comment_read_receipt'),
        ),
        migrations.RunPython(initialize_existing_comments_as_read, migrations.RunPython.noop),
    ]
