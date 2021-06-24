# Generated by Django 2.2.23 on 2021-06-14 13:47

from django.conf import settings
from django.db import migrations, models
from django.db.utils import ProgrammingError


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0049_auto_20210526_1517'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='shared_with_groups',
            field=models.ManyToManyField(blank=True,
                                         related_name='shared_documents',
                                         to='auth.Group',
                                         verbose_name='Share with teams'),
        ),
        migrations.AddField(
            model_name='document',
            name='shared_with_users',
            field=models.ManyToManyField(blank=True,
                                         related_name='shared_documents',
                                         to='users.User',
                                         verbose_name='Share with users'),
        )
    ]

    def apply(self, project_state, schema_editor, collect_sql=False):
        """
        Because we went back on moving the shared_with_groups and shared_with_users fields
        from documents to projects, but some instances might not have migrated yet,
        we may save the sharing on the document level by modifying the deletion of those fields
        in the old migration and discard the exception raised here if they already exists.

        """
        try:
            super().apply(project_state, schema_editor, collect_sql=False)
        except ProgrammingError:
            pass

    def unapply(self, project_state, schema_editor, collect_sql=False):
        """
        Don't do anything here or migration 48 will throw an error when going backwards
        """
        pass
