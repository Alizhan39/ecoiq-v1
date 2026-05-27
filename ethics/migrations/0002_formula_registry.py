"""Data migration: loads all 36 formula definitions into the database."""
from django.db import migrations


def load_formulas(apps, schema_editor):
    from ethics.registry import all_formulas
    FormulaDefinition = apps.get_model('ethics', 'FormulaDefinition')
    for f in all_formulas():
        FormulaDefinition.objects.update_or_create(
            code=f['code'],
            defaults={
                'name':              f['name'],
                'category':          f.get('category', ''),
                'master_formula':    f.get('master_formula', 'ALL'),
                'description':       f['description'],
                'maqasid_principle': f.get('maqasid_principle', ''),
                'weight':            f.get('weight', 1.0),
                'is_public':         f.get('is_public', False),
                'order':             f.get('order', 0),
            },
        )


def unload_formulas(apps, schema_editor):
    FormulaDefinition = apps.get_model('ethics', 'FormulaDefinition')
    FormulaDefinition.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ethics', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_formulas, reverse_code=unload_formulas),
    ]
