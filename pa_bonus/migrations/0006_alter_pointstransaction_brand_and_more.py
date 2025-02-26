# Generated by Django 5.1.6 on 2025-02-26 12:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0005_rewardrequest_rewardrequestitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pointstransaction',
            name='brand',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pa_bonus.brand'),
        ),
        migrations.AlterField(
            model_name='rewardrequest',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('REJECTED', 'Rejected'), ('FINISHED', 'Finished'), ('CANCELLED', 'Cancelled')], default='DRAFT', max_length=20),
        ),
    ]
