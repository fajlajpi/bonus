# Generated by Django 5.1.6 on 2025-05-07 10:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0020_reward_in_showcase'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reward',
            name='availability',
            field=models.CharField(choices=[('AVAILABLE', 'Available'), ('AVAILABLE_LAST_UNITS', 'Available (Last units)'), ('ON_DEMAND', 'On Demand'), ('UNAVAILABLE', 'Unavailable')], default='ON_DEMAND', max_length=20),
        ),
    ]
