# Generated by Django 5.1.6 on 2025-02-26 12:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0006_alter_pointstransaction_brand_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pointstransaction',
            name='reward_request',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pa_bonus.rewardrequest'),
        ),
    ]
