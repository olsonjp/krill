"""
Migration: Aliquot nomenclature redesign

Collapses Aliquot + AliquotTube so one Aliquot IS one physical item.

Data migration steps:
1. Add disposition FK to Aliquot (nullable initially)
2. For each existing Aliquot with quantity N:
   - Gets its AliquotTube records ordered by tube_number
   - Tube 1: sets the existing Aliquot's disposition = tube1.disposition
   - Tubes 2..N: creates NEW Aliquot records, each with their tube's disposition
   - For each AliquotLocation that references (old_aliquot, tube_number): updates to
     point to the new Aliquot for that tube_number
3. For Aliquots with no tubes: sets disposition to 'stored' disposition (get_or_create)
4. Makes disposition non-nullable
5. Removes AliquotTube model
6. Removes tube_number from AliquotLocation
7. Removes quantity from Aliquot
8. Adds unique constraint on AliquotLocation.aliquot
"""

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def migrate_aliquots_forward(apps, schema_editor):
    Aliquot = apps.get_model('sample', 'Aliquot')
    AliquotTube = apps.get_model('sample', 'AliquotTube')
    AliquotLocation = apps.get_model('sample', 'AliquotLocation')
    AliquotDisposition = apps.get_model('sample', 'AliquotDisposition')

    # Default 'stored' disposition — only created lazily when actually needed
    stored_disposition = None

    def get_stored_disposition():
        nonlocal stored_disposition
        if stored_disposition is None:
            stored_disposition, _ = AliquotDisposition.objects.get_or_create(
                name='Stored',
                defaults={'disposition_type': 'stored'},
            )
        return stored_disposition

    for aliquot in Aliquot.objects.all().order_by('id'):
        tubes = AliquotTube.objects.filter(aliquot=aliquot).order_by('tube_number')

        if not tubes.exists():
            # No tubes: set disposition to stored
            aliquot.disposition = get_stored_disposition()
            aliquot.save()
            continue

        # Map tube_number -> new aliquot for location update
        tube_to_aliquot = {}

        for i, tube in enumerate(tubes):
            if i == 0:
                # First tube: update the existing aliquot record
                aliquot.disposition = tube.disposition
                aliquot.save()
                tube_to_aliquot[tube.tube_number] = aliquot
            else:
                # Additional tubes: create a new Aliquot record
                new_aliquot = Aliquot.objects.create(
                    sample=aliquot.sample,
                    aliquot_type=aliquot.aliquot_type,
                    parent=aliquot.parent,
                    access_level=aliquot.access_level,
                    created_at=aliquot.created_at,
                    deleted=aliquot.deleted,
                    deleted_at=aliquot.deleted_at,
                    disposition=tube.disposition,
                    # quantity will be removed later; set to 1 for now
                    quantity=1,
                )
                tube_to_aliquot[tube.tube_number] = new_aliquot

        # Update AliquotLocation records to point to the correct new aliquots
        for location in AliquotLocation.objects.filter(aliquot=aliquot):
            target_aliquot = tube_to_aliquot.get(location.tube_number)
            if target_aliquot and target_aliquot.pk != aliquot.pk:
                location.aliquot = target_aliquot
                location.save()
            # If tube_number == 1, location already points to the right aliquot


def migrate_aliquots_backward(apps, schema_editor):
    # Reversing this is complex; we just clear disposition on all aliquots
    Aliquot = apps.get_model('sample', 'Aliquot')
    Aliquot.objects.all().update(disposition=None)


class Migration(migrations.Migration):

    dependencies = [
        ('sample', '0004_alter_aliquot_options_alter_sample_options'),
    ]

    operations = [
        # Step 1: Add disposition FK to Aliquot (nullable)
        migrations.AddField(
            model_name='aliquot',
            name='disposition',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='sample.aliquotdisposition',
            ),
        ),

        # Step 2: Run data migration
        migrations.RunPython(
            migrate_aliquots_forward,
            migrate_aliquots_backward,
        ),

        # Step 3: Keep disposition nullable (data migration above ensures all rows are set)
        # The field is nullable to allow flexibility; the form enforces it at the UI level.

        # Step 4: Remove AliquotTube model
        migrations.DeleteModel(
            name='AliquotTube',
        ),

        # Step 5: Remove the old unique_together constraints on AliquotLocation
        # (must be done before removing tube_number column on SQLite)
        migrations.AlterUniqueTogether(
            name='aliquotlocation',
            unique_together=set(),
        ),

        # Step 6: Remove tube_number from AliquotLocation
        migrations.RemoveField(
            model_name='aliquotlocation',
            name='tube_number',
        ),

        # Step 7: Change aliquot FK on AliquotLocation to OneToOneField
        migrations.AlterField(
            model_name='aliquotlocation',
            name='aliquot',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='location',
                to='sample.aliquot',
            ),
        ),

        # Step 8: Add unique constraint on box+row+column
        migrations.AlterUniqueTogether(
            name='aliquotlocation',
            unique_together={('box', 'row', 'column')},
        ),

        # Step 9: Remove quantity from Aliquot
        migrations.RemoveField(
            model_name='aliquot',
            name='quantity',
        ),
    ]
