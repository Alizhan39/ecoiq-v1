"""Project-owned, source-linked, explicitly unverified KPI input claims.

Migration has no data backfill: historic CSV summaries must never be recast as
verified measurements.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0004_process_ai_review'),
        ('evidence_memory', '0005_evidencememory_legal_status_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessKPIMeasurementClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('formula_key', models.CharField(max_length=50)),
                ('input_key', models.CharField(max_length=50)),
                ('value_decimal', models.DecimalField(decimal_places=18, max_digits=44)),
                ('unit', models.CharField(max_length=30)),
                ('period', models.CharField(max_length=7)),
                ('source_chunk_sha256', models.CharField(max_length=64)),
                ('formula_spec_sha256', models.CharField(max_length=64)),
                ('review_status', models.CharField(
                    choices=[('REPORTED_NOT_VERIFIED', 'Reported, not verified')],
                    default='REPORTED_NOT_VERIFIED', editable=False, max_length=32,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('analysis', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='kpi_measurement_claims', to='api.processanalysisrun',
                )),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='created_process_kpi_measurement_claims',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('evidence', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='process_kpi_measurement_claims',
                    to='evidence_memory.evidencememory',
                )),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='process_kpi_measurement_claims',
                    to='gold_intelligence.goldproject',
                )),
            ],
            options={
                'ordering': ['-created_at', '-pk'],
                'indexes': [
                    models.Index(
                        fields=['project', 'analysis', '-created_at'],
                        name='api_kpi_claim_project_run_idx',
                    ),
                ],
                'constraints': [
                    models.CheckConstraint(
                        condition=models.Q(review_status='REPORTED_NOT_VERIFIED'),
                        name='api_kpi_claim_never_auto_verif',
                    ),
                ],
            },
        ),
    ]
