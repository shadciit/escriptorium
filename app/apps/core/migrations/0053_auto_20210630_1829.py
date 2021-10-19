# Generated by Django 2.2.24 on 2021-06-30 18:29

import core.models
import core.utils
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_document_line_offset'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('color', core.utils.ColorField(default=core.models.random_color, max_length=7)),
                ('project', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='document_tags', to='core.Project')),
            ],
            options={
                'unique_together': {('project', 'name')},
            },
        ),
        migrations.AddField(
            model_name='document',
            name='tags',
            field=models.ManyToManyField(blank=True, to='core.DocumentTag'),
        ),
    ]
