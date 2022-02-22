# Generated by Django 2.1.4 on 2019-05-29 09:43
from django.db import connection
from django.db import migrations


def forward(apps, se):
    with connection.cursor() as cursor:
        # format lines and blocks to polygons, it won't bother because it's a jsonfield
        res = cursor.execute("UPDATE core_line SET box=array_to_json("
                             "('{{' || CAST(box->0 as text) || ',' || CAST(box->1 as text) || '},"
                             "{' || CAST(box->0 as text) || ',' || CAST(box->3 as text) || '},"
                             "{' || CAST(box->2 as text) || ',' || CAST(box->3 as text) || '},"
                             "{' || CAST(box->2 as text) || ',' || CAST(box->1 as text) || '}}')::int[])")


def backward(apps, se):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE core_line SET box=array_to_json("
                       "('{' || CAST(box->0->0 as text) || ',' || CAST(box->0->1 as text) || ','"
                       "|| CAST(box->2->0 as text) || ',' || CAST(box->2->1 as text) || '}')::int[])")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_ocrmodel_training_epoch'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='transcription',
            options={'ordering': ('-updated_at',)},
        ),
        migrations.RunPython(forward, backward),
        migrations.RenameField(
            model_name='line',
            old_name='box',
            new_name='polygon',
        )
    ]
