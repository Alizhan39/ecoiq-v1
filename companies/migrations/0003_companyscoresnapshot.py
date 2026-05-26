from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0002_add_harm_penalty_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyScoreSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(help_text='Date this score was recorded / effective from')),
                ('trigger', models.CharField(
                    choices=[
                        ('manual',        'Manual (Admin)'),
                        ('annual_review', 'Annual Review'),
                        ('report_update', 'New Report / Evidence'),
                        ('verification',  'Profile Verification'),
                        ('transition',    'Transition Milestone'),
                        ('seed',          'Initial Seed Score'),
                    ],
                    default='manual', max_length=30,
                )),
                ('total_score',             models.FloatField()),
                ('public_benefit_score',    models.FloatField(default=50.0)),
                ('environmental_score',     models.FloatField(default=50.0)),
                ('modernization_score',     models.FloatField(default=50.0)),
                ('governance_score',        models.FloatField(default=50.0)),
                ('anti_corruption_score',   models.FloatField(default=50.0)),
                ('ethical_alignment_score', models.FloatField(default=50.0)),
                ('harm_penalty',            models.FloatField(default=0.0)),
                ('moral_label', models.CharField(blank=True, max_length=40)),
                ('notes', models.TextField(blank=True, help_text='Context — event, data source, milestone')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='score_snapshots',
                    to='companies.companyprofile',
                )),
            ],
            options={
                'verbose_name':        'Score Snapshot',
                'verbose_name_plural': 'Score Snapshots',
                'ordering':            ['-date'],
            },
        ),
    ]
