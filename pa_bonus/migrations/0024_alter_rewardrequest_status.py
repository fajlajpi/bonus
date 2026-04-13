from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0023_alter_usercontractgoal_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rewardrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('PENDING', 'Pending'),
                    ('ACCEPTED', 'Accepted'),
                    ('REJECTED', 'Rejected'),
                    ('FINISHED', 'Finished'),
                    ('CANCELLED', 'Cancelled'),
                    ('OVERDUE_INVOICE', 'Faktura po splatnosti'),
                ],
                default='DRAFT',
                max_length=20,
            ),
        ),
    ]
