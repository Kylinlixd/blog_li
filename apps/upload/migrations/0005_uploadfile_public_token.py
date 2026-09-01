import uuid

from django.db import migrations, models


def _unique_token(upload_file_model):
    while True:
        token = uuid.uuid4().hex
        if not upload_file_model.objects.filter(public_token=token).exists():
            return token


def _replace_in_value(value, replacements):
    if not isinstance(value, str):
        return value
    for old, new in replacements:
        value = value.replace(old, new)
    return value


def tokenize_public_file_urls(apps, schema_editor):
    UploadFile = apps.get_model("upload", "UploadFile")
    Dynamic = apps.get_model("dynamic", "Dynamic")

    replacements = []
    for file_record in UploadFile.objects.filter(is_public=True).order_by("pk"):
        token = _unique_token(UploadFile)
        old_file_url = f"/api/upload/public/{file_record.pk}/"
        new_file_url = f"/api/upload/public/{token}/"
        old_poster_url = f"/api/upload/poster/{file_record.pk}/"
        new_poster_url = f"/api/upload/poster/{token}/"

        replacements.append((old_file_url, new_file_url))
        replacements.append((old_poster_url, new_poster_url))

        file_record.public_token = token
        if file_record.file_url == old_file_url:
            file_record.file_url = new_file_url
        if file_record.poster_url == old_poster_url:
            file_record.poster_url = new_poster_url
        file_record.save(update_fields=["public_token", "file_url", "poster_url"])

    for dynamic in Dynamic.objects.all().iterator():
        if isinstance(dynamic.media_urls, list):
            dynamic.media_urls = [
                _replace_in_value(url, replacements) for url in dynamic.media_urls
            ]
        else:
            dynamic.media_urls = _replace_in_value(dynamic.media_urls, replacements)
        dynamic.content = _replace_in_value(dynamic.content or "", replacements)
        dynamic.save(update_fields=["media_urls", "content"])


class Migration(migrations.Migration):
    dependencies = [
        ("dynamic", "0008_dynamiclike"),
        ("upload", "0004_uploadfile_poster_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadfile",
            name="public_token",
            field=models.CharField(
                blank=True,
                help_text="公开下载脱敏令牌",
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(
            tokenize_public_file_urls,
            migrations.RunPython.noop,
        ),
    ]
