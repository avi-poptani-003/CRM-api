# Generated by Django 5.0 on 2025-06-09 11:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0003_lead_property'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lead',
            name='tags',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]
