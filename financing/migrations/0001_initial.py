from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('companies', '0001_initial'),
        ('transition', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyFinancingProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='financing_intel',
                    to='companies.companyprofile',
                )),
                # Readiness scores
                ('financing_readiness',      models.FloatField(default=0.0)),
                ('modernization_readiness',  models.FloatField(default=0.0)),
                ('transparency_readiness',   models.FloatField(default=0.0)),
                ('climate_readiness',        models.FloatField(default=0.0)),
                ('governance_readiness',     models.FloatField(default=0.0)),
                ('evidence_completeness',    models.FloatField(default=0.0)),
                # Tier & urgency
                ('readiness_tier', models.CharField(
                    choices=[
                        ('investment_ready', 'Investment Ready'),
                        ('nearly_ready',     'Nearly Ready'),
                        ('developing',       'Developing'),
                        ('early_stage',      'Early Stage'),
                    ],
                    default='early_stage', max_length=20,
                )),
                ('funding_urgency', models.CharField(
                    choices=[
                        ('critical', 'Critical — Immediate Need'),
                        ('high',     'High — 1–2 Years'),
                        ('medium',   'Medium — 2–5 Years'),
                        ('low',      'Low — Long-term'),
                    ],
                    default='medium', max_length=15,
                )),
                # Financial intelligence
                ('estimated_capex_low_usd',      models.BigIntegerField(blank=True, null=True)),
                ('estimated_capex_high_usd',     models.BigIntegerField(blank=True, null=True)),
                ('estimated_annual_impact_usd',  models.BigIntegerField(blank=True, null=True)),
                # Gap analysis
                ('missing_requirements', models.JSONField(blank=True, default=list)),
                ('next_actions',         models.JSONField(blank=True, default=list)),
                # AI narrative
                ('ai_financing_narrative', models.TextField(blank=True)),
                ('ai_gap_analysis',        models.TextField(blank=True)),
                # Confidence + workflow
                ('confidence',       models.FloatField(default=0.5)),
                ('last_computed',    models.DateTimeField(auto_now=True)),
                ('analyst_reviewed', models.BooleanField(default=False)),
                ('analyst_notes',    models.TextField(blank=True)),
            ],
            options={
                'verbose_name':        'Company Financing Profile',
                'verbose_name_plural': 'Company Financing Profiles',
            },
        ),
        migrations.CreateModel(
            name='DirectFinancingMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='financing_matches',
                    to='companies.companyprofile',
                )),
                ('opportunity', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='direct_matches',
                    to='transition.financingopportunity',
                )),
                ('match_score',  models.FloatField(default=0.0)),
                ('match_tier', models.CharField(
                    choices=[
                        ('eligible',  'Eligible'),
                        ('likely',    'Likely Eligible'),
                        ('potential', 'Potential'),
                        ('unlikely',  'Unlikely'),
                    ],
                    default='potential', max_length=15,
                )),
                ('match_rationale',      models.TextField(blank=True)),
                ('missing_requirements', models.JSONField(blank=True, default=list)),
                ('next_steps',           models.JSONField(blank=True, default=list)),
                ('recommended_amount_usd', models.BigIntegerField(blank=True, null=True)),
                ('is_featured',  models.BooleanField(default=False)),
                ('computed_at',  models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name':        'Direct Financing Match',
                'verbose_name_plural': 'Direct Financing Matches',
                'ordering':            ['-match_score'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='directfinancingmatch',
            unique_together={('profile', 'opportunity')},
        ),
    ]
