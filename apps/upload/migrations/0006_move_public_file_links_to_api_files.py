from django.db import migrations


def _replace_prefix(value):
    if not isinstance(value, str):
        return value
    return value.replace("/api/upload/public/", "/api/files/public/").replace(
        "/api/upload/poster/", "/api/files/poster/"
    )


def move_public_links_to_api_files(apps, schema_editor):
    UploadFile = apps.get_model("upload", "UploadFile")
    Dynamic = apps.get_model("dynamic", "Dynamic")

    for file_record in UploadFile.objects.all().iterator():
        file_record.file_url = _replace_prefix(file_record.file_url)
        file_record.poster_url = _replace_prefix(file_record.poster_url)
        file_record.save(update_fields=["file_url", "poster_url"])

    for dynamic in Dynamic.objects.all().iterator():
        if isinstance(dynamic.media_urls, list):
            dynamic.media_urls = [
                _replace_prefix(url) for url in dynamic.media_urls
            ]
        else:
            dynamic.media_urls = _replace_prefix(dynamic.media_urls)
        dynamic.content = _replace_prefix(dynamic.content or "")
        dynamic.save(update_fields=["media_urls", "content"])


class Migration(migrations.Migration):
    dependencies = [
        ("dynamic", "0008_dynamiclike"),
        ("upload", "0005_uploadfile_public_token"),
    ]

    operations = [
        migrations.RunPython(
            move_public_links_to_api_files,
            migrations.RunPython.noop,
        ),
    ]
