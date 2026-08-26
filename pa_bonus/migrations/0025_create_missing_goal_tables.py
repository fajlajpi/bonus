"""
Recovery migration for the goal tables.

HISTORY
-------
On the original production database, migrations 0011 and 0023 were recorded as
applied even though pa_bonus_usercontractgoal and pa_bonus_goalevaluation were
never physically created. This migration existed to repair that specific
database by creating the two tables outright.

That made the migration set impossible to replay from zero: on a fresh database
0011 and 0023 create the tables correctly, and this migration then failed with
"relation pa_bonus_usercontractgoal already exists". The documented workaround
was to run it with --fake on every new deployment.

CURRENT BEHAVIOUR
-----------------
The table creation is now conditional. Each table is created only if it is
genuinely absent from the database:

  * Fresh database - 0011/0023 already built both tables, so this migration
    inspects them, finds them present, and does nothing. No --fake required.
  * Database in the historical broken state - the tables are missing, so they
    are created here exactly as before. The recovery path still works.

The models are already present in the migration state after 0011 and 0023, so
this migration deliberately makes no state changes; it only reconciles the
database with that state.
"""
from django.db import migrations

GOAL_MODELS = ('UserContractGoal', 'GoalEvaluation')


def create_goal_tables_if_missing(apps, schema_editor):
    """Create the goal tables only on databases where they are absent."""
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    for model_name in GOAL_MODELS:
        model = apps.get_model('pa_bonus', model_name)
        if model._meta.db_table not in existing_tables:
            schema_editor.create_model(model)


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0024_alter_rewardrequest_status'),
    ]

    operations = [
        migrations.RunPython(
            create_goal_tables_if_missing,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
