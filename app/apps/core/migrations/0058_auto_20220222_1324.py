# Generated by Django 2.2.27 on 2022-02-22 13:24

import core.utils
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0057_auto_20210730_1449'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnnotationComponent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=128)),
                ('allowed_values', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=128), blank=True, help_text='Comma separated list of possible value, leave it empty for free input.', null=True, size=None)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Document')),
            ],
        ),
        migrations.CreateModel(
            name='AnnotationTaxonomy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(db_index=True, editable=False, verbose_name='order')),
                ('has_comments', models.BooleanField(default=False)),
                ('name', models.CharField(max_length=64)),
                ('marker_type', models.PositiveSmallIntegerField(choices=[(1, 'Rectangle'), (2, 'Polygon'), (3, 'Background Color'), (4, 'Text Color'), (5, 'Bold'), (6, 'Italic')])),
                ('marker_detail', core.utils.ColorField(blank=True, default=core.utils.random_color, max_length=7, null=True)),
                ('components', models.ManyToManyField(blank=True, related_name='taxonomy', to='core.AnnotationComponent')),
                ('document', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Document')),
            ],
            options={
                'ordering': ('order',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AnnotationType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('public', models.BooleanField(default=False)),
                ('default', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            }
        ),
        migrations.CreateModel(
            name='ImageAnnotation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comments', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), blank=True, null=True, size=None)),
                ('coordinates', django.contrib.postgres.fields.ArrayField(base_field=django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), size=2), size=None)),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.DocumentPart')),
                ('taxonomy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.AnnotationTaxonomy')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TextAnnotation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comments', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), blank=True, null=True, size=None)),
                ('start_offset', models.PositiveIntegerField()),
                ('end_offset', models.PositiveIntegerField()),
                ('end_line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotations_ends', to='core.Line')),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.DocumentPart')),
                ('start_line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotation_starts', to='core.Line')),
                ('taxonomy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.AnnotationTaxonomy')),
                ('transcription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Transcription')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TextAnnotationComponentValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=256)),
                ('annotation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='components', to='core.TextAnnotation')),
                ('component', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.AnnotationComponent')),
            ],
        ),
        migrations.CreateModel(
            name='ImageAnnotationComponentValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=256)),
                ('annotation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='components', to='core.ImageAnnotation')),
                ('component', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.AnnotationComponent')),
            ],
        ),
        migrations.AddField(
            model_name='annotationtaxonomy',
            name='typology',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.AnnotationType'),
        ),
    ]
