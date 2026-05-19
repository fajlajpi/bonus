from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0026_abra_integration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rewardrequest',
            name='status',
            field=models.CharField(
                max_length=25,
                choices=[
                    ('DRAFT', 'Draft'),
                    ('PENDING', 'Pending'),
                    ('ACCEPTED', 'Accepted'),
                    ('SHIPPED', 'Shipped'),
                    ('PARTIALLY_SHIPPED', 'Partially shipped'),
                    ('ORDERED_FROM_SUPPLIER', 'Ordered from supplier'),
                    ('REJECTED', 'Rejected'),
                    ('FINISHED', 'Finished'),
                    ('CANCELLED', 'Cancelled'),
                    ('OVERDUE_INVOICE', 'Faktura po splatnosti'),
                ],
                default='DRAFT',
            ),
        ),
    ]
