from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('access_log', '0004_ipgeocache'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='accesslog',
            name='security_action',
            field=models.CharField(blank=True, default='', max_length=24),
        ),
        migrations.AddField(
            model_name='accesslog',
            name='security_rule',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='access_logs', to='access_log.ipsecurityrule'),
        ),
    ]
