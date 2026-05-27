import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('companies', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FormulaDefinition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(help_text='Short code, e.g. EB_01, NEI', max_length=10, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('category', models.CharField(
                    blank=True,
                    choices=[
                        ('environmental_balance',    'Environmental Balance'),
                        ('industrial_efficiency',    'Industrial Efficiency'),
                        ('transparency_governance',  'Transparency & Governance'),
                        ('public_benefit',           'Public Benefit'),
                        ('restoration_regeneration', 'Restoration & Regeneration'),
                        ('long_term_sustainability', 'Long-Term Sustainability'),
                        ('ethical_capital',          'Ethical Capital Allocation'),
                        ('anti_corruption',          'Anti-Corruption & Accountability'),
                    ],
                    max_length=30,
                    help_text='Blank for master formulas',
                )),
                ('master_formula', models.CharField(
                    choices=[
                        ('NEI', 'Net Ethical Impact'),
                        ('TSS', 'Transition Stewardship Score'),
                        ('RVI', 'Regenerative Value Index'),
                        ('ALL', 'Cross-cutting / All Formulas'),
                    ],
                    default='ALL',
                    max_length=5,
                )),
                ('description', models.TextField()),
                ('methodology_notes', models.TextField(blank=True)),
                ('input_fields', models.JSONField(blank=True, default=list)),
                ('maqasid_principle', models.CharField(
                    blank=True,
                    choices=[
                        ('life',     'Preservation of Life & Health'),
                        ('intellect','Preservation of Intellect & Knowledge'),
                        ('wealth',   'Preservation of Real Wealth & Value'),
                        ('society',  'Preservation of Society & Future Generations'),
                        ('trust',    'Preservation of Trust & Ethical Integrity'),
                    ],
                    max_length=15,
                )),
                ('maqasid_notes', models.TextField(blank=True)),
                ('weight', models.FloatField(default=1.0)),
                ('is_public', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Formula Definition',
                'verbose_name_plural': 'Formula Definitions',
                'ordering': ['category', 'order', 'code'],
            },
        ),
        migrations.CreateModel(
            name='CompanyEthicsProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ethics',
                    to='companies.companyprofile',
                )),
                ('net_ethical_impact',     models.FloatField(default=0.0)),
                ('transition_stewardship', models.FloatField(default=0.0)),
                ('regenerative_value',     models.FloatField(default=0.0)),
                ('total_benefit_score',    models.FloatField(default=0.0)),
                ('total_harm_score',       models.FloatField(default=0.0)),
                ('key_harms',              models.JSONField(blank=True, default=list)),
                ('key_benefits',           models.JSONField(blank=True, default=list)),
                ('next_best_actions',      models.JSONField(blank=True, default=list)),
                ('expected_score_improvement', models.FloatField(blank=True, null=True)),
                ('data_confidence',        models.FloatField(default=0.5)),
                ('analyst_reviewed',       models.BooleanField(default=False)),
                ('analyst_approved',       models.BooleanField(default=False)),
                ('analyst_reviewed_at',    models.DateTimeField(blank=True, null=True)),
                ('analyst_reviewer', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('analyst_notes_text', models.TextField(blank=True)),
                ('last_computed',   models.DateTimeField(auto_now=True)),
                ('formula_version', models.CharField(default='1.0', max_length=10)),
            ],
            options={
                'verbose_name': 'Company Ethics Profile',
                'verbose_name_plural': 'Company Ethics Profiles',
            },
        ),
        migrations.CreateModel(
            name='FormulaScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ethics_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='formula_scores',
                    to='ethics.companyethicsprofile',
                )),
                ('formula', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='company_scores',
                    to='ethics.formuladefinition',
                )),
                ('raw_value',        models.FloatField()),
                ('normalized_score', models.FloatField()),
                ('confidence',       models.FloatField(default=0.5)),
                ('evidence_notes',   models.TextField(blank=True)),
                ('evidence_verified',models.BooleanField(default=False)),
                ('source_urls',      models.JSONField(blank=True, default=list)),
                ('analyst_adjusted', models.BooleanField(default=False)),
                ('analyst_override', models.FloatField(blank=True, null=True)),
                ('analyst_reason',   models.TextField(blank=True)),
                ('computed_at',      models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Formula Score',
                'verbose_name_plural': 'Formula Scores',
                'ordering': ['formula__category', 'formula__order'],
                'unique_together': {('ethics_profile', 'formula')},
            },
        ),
        migrations.CreateModel(
            name='ImprovementMilestone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ethics_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='milestones',
                    to='ethics.companyethicsprofile',
                )),
                ('title',       models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('formula_category', models.CharField(
                    blank=True,
                    choices=[
                        ('environmental_balance',    'Environmental Balance'),
                        ('industrial_efficiency',    'Industrial Efficiency'),
                        ('transparency_governance',  'Transparency & Governance'),
                        ('public_benefit',           'Public Benefit'),
                        ('restoration_regeneration', 'Restoration & Regeneration'),
                        ('long_term_sustainability', 'Long-Term Sustainability'),
                        ('ethical_capital',          'Ethical Capital Allocation'),
                        ('anti_corruption',          'Anti-Corruption & Accountability'),
                    ],
                    max_length=30,
                )),
                ('pillar',       models.CharField(blank=True, max_length=50)),
                ('expected_score_gain', models.FloatField(default=0.0)),
                ('effort_level', models.CharField(
                    choices=[('low','Low'),('medium','Medium'),('high','High')],
                    default='medium', max_length=10,
                )),
                ('timeline_months', models.PositiveSmallIntegerField(default=6)),
                ('priority',     models.PositiveSmallIntegerField(default=5)),
                ('status', models.CharField(
                    choices=[
                        ('recommended', 'Recommended'),
                        ('in_progress', 'In Progress'),
                        ('completed',   'Completed'),
                        ('deferred',    'Deferred'),
                    ],
                    default='recommended', max_length=15,
                )),
                ('completed_at',   models.DateTimeField(blank=True, null=True)),
                ('kpi_metric',     models.CharField(blank=True, max_length=255)),
                ('target_value',   models.CharField(blank=True, max_length=100)),
                ('current_value',  models.CharField(blank=True, max_length=100)),
                ('maqasid_principle', models.CharField(
                    blank=True,
                    choices=[
                        ('life',     'Preservation of Life & Health'),
                        ('intellect','Preservation of Intellect & Knowledge'),
                        ('wealth',   'Preservation of Real Wealth & Value'),
                        ('society',  'Preservation of Society & Future Generations'),
                        ('trust',    'Preservation of Trust & Ethical Integrity'),
                    ],
                    max_length=15,
                )),
                ('order',      models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Improvement Milestone',
                'verbose_name_plural': 'Improvement Milestones',
                'ordering': ['priority', 'order'],
            },
        ),
        migrations.CreateModel(
            name='AnalystNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ethics_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='analyst_notes_set',
                    to='ethics.companyethicsprofile',
                )),
                ('formula_score', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='analyst_notes',
                    to='ethics.formulascore',
                )),
                ('author', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('note_type', models.CharField(
                    choices=[
                        ('observation',  'Observation'),
                        ('flag',         'Flag for Review'),
                        ('verification', 'Verification Note'),
                        ('approval',     'Approval'),
                        ('correction',   'Correction'),
                    ],
                    default='observation', max_length=15,
                )),
                ('note',      models.TextField()),
                ('is_public', models.BooleanField(default=False)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('updated_at',models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Analyst Note',
                'verbose_name_plural': 'Analyst Notes',
                'ordering': ['-created_at'],
            },
        ),
    ]
