# Generated by Django 2.2.24 on 2021-11-24 14:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0062_ocrmodel_cluster_job'),
    ]

    operations = [
        migrations.RenameField(
            model_name='clusterjob',
            old_name='job_workdir',
            new_name='job_uuid',
        ),
    ]
