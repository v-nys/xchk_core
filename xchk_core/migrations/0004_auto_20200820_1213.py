# Generated by Django 2.2.15 on 2020-08-20 12:13

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('xchk_core', '0003_auto_20200820_1105'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='SubmissionV2',
            new_name='Submission',
        ),
    ]