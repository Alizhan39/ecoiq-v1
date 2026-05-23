from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='finding',
            name='root_cause',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='finding',
            name='recommended_action',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='finding',
            name='efficiency_gain_pct',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='finding',
            name='sustainability_impact',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='auditreport',
            name='energy_reduction_pct',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='auditreport',
            name='downtime_reduction_pct',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='auditreport',
            name='production_efficiency_pct',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='auditreport',
            name='emissions_reduction_pct',
            field=models.IntegerField(default=0),
        ),
    ]
