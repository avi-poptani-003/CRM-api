# Generated by Django 5.0 on 2025-05-26 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_profile_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='password_last_changed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
