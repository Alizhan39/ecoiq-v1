from django.db import migrations

from heating.seed_data import PACKAGE_SEED


def seed_packages(apps, schema_editor):
    HeatingPackage = apps.get_model('heating', 'HeatingPackage')
    for row in PACKAGE_SEED:
        HeatingPackage.objects.update_or_create(slug=row['slug'], defaults=row)


def unseed_packages(apps, schema_editor):
    HeatingPackage = apps.get_model('heating', 'HeatingPackage')
    slugs = [r['slug'] for r in PACKAGE_SEED]
    HeatingPackage.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('heating', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_packages, unseed_packages),
    ]
