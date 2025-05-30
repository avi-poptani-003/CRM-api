# Generated by Django 5.0 on 2025-05-19 04:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('property', '0002_alter_propertyimage_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='propertyimage',
            options={'ordering': ['-is_primary', '-created_at']},
        ),
        migrations.AddField(
            model_name='propertyimage',
            name='is_primary',
            field=models.BooleanField(default=False),
        ),
    ]
