"""
Recovery migration: creates pa_bonus_usercontractgoal and pa_bonus_goalevaluation
which were never physically created in the database despite migrations 0011 and 0023
being recorded as applied. Run after faking 0011-0024.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0024_alter_rewardrequest_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Creates the table with ALL fields it should currently have
        # (base fields from 0011 + extra fields added by 0023)
        migrations.CreateModel(
            name='UserContractGoal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('goal_period_from', models.DateField()),
                ('goal_period_to', models.DateField()),
                ('goal_value', models.IntegerField()),
                ('goal_base', models.IntegerField()),
                ('allow_full_period_recovery', models.BooleanField(
                    default=True,
                    help_text='If True, missing early milestones can be recovered if full period goal is met',
                )),
                ('bonus_percentage', models.FloatField(
                    default=0.5,
                    help_text='Percentage of exceeded amount to award as points (0.5 = 50%)',
                )),
                ('evaluation_frequency', models.IntegerField(
                    default=6,
                    help_text='How often to evaluate progress (in months)',
                )),
                ('brands', models.ManyToManyField(to='pa_bonus.brand')),
                ('user_contract', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='extra_goals',
                    to='pa_bonus.usercontract',
                )),
            ],
            options={
                'ordering': ['-goal_period_from'],
            },
        ),
        migrations.CreateModel(
            name='GoalEvaluation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('evaluation_date', models.DateField()),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('actual_turnover', models.DecimalField(decimal_places=2, max_digits=12)),
                ('target_turnover', models.DecimalField(decimal_places=2, max_digits=12)),
                ('baseline_turnover', models.DecimalField(decimal_places=2, max_digits=12)),
                ('is_achieved', models.BooleanField(default=False)),
                ('bonus_points', models.IntegerField(default=0)),
                ('evaluation_type', models.CharField(
                    choices=[
                        ('MILESTONE', 'Milestone Evaluation'),
                        ('RECOVERY', 'Full Period Recovery'),
                        ('FINAL', 'Final Evaluation'),
                    ],
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('evaluated_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ('goal', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='evaluations',
                    to='pa_bonus.usercontractgoal',
                )),
                ('points_transaction', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='pa_bonus.pointstransaction',
                )),
            ],
            options={
                'ordering': ['-evaluation_date'],
                'unique_together': {('goal', 'period_end')},
            },
        ),
    ]
