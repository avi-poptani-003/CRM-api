# Generated by Django 5.0 on 2025-05-27 04:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('property', '0003_alter_propertyimage_options_propertyimage_is_primary'),
    ]

    operations = [
        migrations.AlterField(
            model_name='property',
            name='property_type',
            field=models.CharField(choices=[('House', 'house'), ('Commercial', 'commercial'), ('Land', 'land')], max_length=20),
        ),
    ]
