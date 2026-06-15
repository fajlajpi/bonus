from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0029_backfill_point_allocations'),
    ]

    operations = [
        # Make reward FK nullable (supports custom items with no linked Reward)
        migrations.AlterField(
            model_name='rewardrequestitem',
            name='reward',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='pa_bonus.reward',
            ),
        ),
        # Custom item fields
        migrations.AddField(
            model_name='rewardrequestitem',
            name='custom_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='rewardrequestitem',
            name='custom_abra_code',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        # Partial shipment tracking
        migrations.AddField(
            model_name='rewardrequestitem',
            name='shipped',
            field=models.BooleanField(default=False),
        ),
        # ABRA submission history
        migrations.CreateModel(
            name='AbraSubmission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('abra_order_id', models.CharField(max_length=20)),
                ('abra_displayname', models.CharField(max_length=50)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('reward_request', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='abra_submissions',
                    to='pa_bonus.rewardrequest',
                )),
            ],
            options={
                'ordering': ['-submitted_at'],
            },
        ),
    ]
