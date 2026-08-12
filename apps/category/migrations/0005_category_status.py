from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('category', '0004_alter_category_options_remove_category_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='status',
            field=models.CharField(
                choices=[('active', '启用'), ('inactive', '禁用')],
                default='active',
                help_text='分类状态',
                max_length=10,
            ),
        ),
    ]
