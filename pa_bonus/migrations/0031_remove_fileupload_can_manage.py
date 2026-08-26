"""
Drops the unused 'can_manage' permission from FileUpload.

The permission was declared in 0002 but never did any work: no view or template
ever checked it, and the data migration meant to grant it always failed (model
permissions do not exist yet while data migrations run). Manager access is
decided solely by membership of the 'Managers' group - see
pa_bonus.utilities.is_manager.

Note that Django does not delete permission rows when they are removed from a
model's Meta. On databases where 0002 already ran, the pa_bonus.can_manage row
survives as an orphan and can be deleted by hand if desired; it grants access to
nothing. Fresh databases never create it.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0030_rewardrequestitem_updates_abrasubmission'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='fileupload',
            options={'ordering': ['-uploaded_at']},
        ),
    ]
