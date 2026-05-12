# Generated as part of the ABRA GEN integration feature.
# Adds:
#   - Reward.is_in_abra_storecards (bool, default True)
#   - RewardRequest.abra_submitted_at (datetime, nullable)
#   - RewardRequest.abra_order_id (char, blank)
#   - RewardRequest.abra_displayname (char, blank)
#
# All defaults are data-safe: existing Reward rows become is_in_abra_storecards=True
# (matching the implicit assumption of the original system), and the three new
# RewardRequest fields are null/empty for all historical rows.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Bump this to whatever your last migration number actually is.
        ('pa_bonus', '0025_create_missing_goal_tables'),
    ]

    operations = [
        migrations.AddField(
            model_name='reward',
            name='is_in_abra_storecards',
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Whether this reward exists as a storecard in ABRA. "
                    "If False, submissions to ABRA will use a text+price line pair "
                    "(rowtype 2 + rowtype 1 cancelling discount) instead of a "
                    "storecard row."
                ),
            ),
        ),
        migrations.AddField(
            model_name='rewardrequest',
            name='abra_submitted_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="When this request was successfully posted to ABRA as a Received Order.",
            ),
        ),
        migrations.AddField(
            model_name='rewardrequest',
            name='abra_order_id',
            field=models.CharField(
                max_length=20,
                blank=True,
                default='',
                help_text="The ABRA internal id of the Received Order created for this request, e.g. 'NM2I700101'.",
            ),
        ),
        migrations.AddField(
            model_name='rewardrequest',
            name='abra_displayname',
            field=models.CharField(
                max_length=50,
                blank=True,
                default='',
                help_text="The ABRA display name of the created order, e.g. 'OP-924/2026'.",
            ),
        ),
    ]
