import uuid
from django.db import migrations, models


def backfill_share_tokens(apps, schema_editor):
    """Assign a unique UUID to every existing Assessment row."""
    Assessment = apps.get_model('core', 'Assessment')
    for obj in Assessment.objects.all():
        obj.share_token = uuid.uuid4()
        obj.save(update_fields=['share_token'])


class Migration(migrations.Migration):
    """
    Three-step migration required by Django 5.2 for callable-default unique fields:
    1. Add column without UNIQUE (all rows get the model-level default).
    2. RunPython to backfill each existing row with its own distinct UUID.
    3. AlterField to add the UNIQUE constraint once values are distinct.
    """

    dependencies = [
        ('core', '0002_finding_pillar_notes'),
    ]

    operations = [
        # 1 — add column (no unique yet; existing rows get a single default value)
        migrations.AddField(
            model_name='assessment',
            name='share_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        # 2 — give every existing row its own unique token
        migrations.RunPython(backfill_share_tokens, migrations.RunPython.noop),
        # 3 — enforce uniqueness now that all values are distinct
        migrations.AlterField(
            model_name='assessment',
            name='share_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
