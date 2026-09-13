from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def seed_read_states(apps, schema_editor):
    Comment = apps.get_model('comment', 'Comment')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    State = apps.get_model('comment', 'CommentReadState')
    max_id = Comment.objects.exclude(status='rejected').order_by('-id').values_list('id', flat=True).first() or 0
    editor_filter = models.Q(role__in=['admin', 'editor', 'moderator']) | models.Q(is_staff=True) | models.Q(is_superuser=True)
    now = timezone.now()
    State.objects.bulk_create([
        State(user_id=user.id, last_seen_comment_id=max_id, initialized_at=now, updated_at=now)
        for user in User.objects.filter(editor_filter).only('id')
    ], ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('comment', '0006_commentreadreceipt'),
    ]
    operations = [
        migrations.CreateModel(
            name='CommentReadState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_seen_comment_id', models.PositiveBigIntegerField(default=0)),
                ('initialized_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='comment_read_state', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'comment_read_state'},
        ),
        migrations.RunPython(seed_read_states, migrations.RunPython.noop),
    ]
