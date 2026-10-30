"""Stage 7: human question review, audit and non-authorising processing checklist."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0003_processanalysisrun'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessAIReviewCase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('questions', models.JSONField(default=list)),
                ('source_manifest', models.JSONField(default=list)),
                ('content_sha256', models.CharField(max_length=64)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending human review'),
                        ('accepted_for_study', 'Accepted as study questions'),
                        ('rejected', 'Rejected'),
                        ('needs_revision', 'Needs revision'),
                    ], default='pending', max_length=24,
                )),
                ('reason_code', models.CharField(blank=True, max_length=32)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('analysis', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='ai_review_cases', to='api.processanalysisrun',
                )),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='process_ai_review_cases', to='gold_intelligence.goldproject',
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='completed_ai_reviews', to=settings.AUTH_USER_MODEL,
                )),
                ('submitted_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='submitted_ai_reviews', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at', '-pk'],
                'indexes': [
                    models.Index(fields=['project', 'status'], name='api_ai_review_project_status'),
                ],
            },
        ),
        migrations.CreateModel(
            name='ProcessAIReviewEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=24)),
                ('reason_code', models.CharField(blank=True, max_length=32)),
                ('content_sha256', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='process_ai_review_events', to=settings.AUTH_USER_MODEL,
                )),
                ('case', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='events', to='api.processaireviewcase',
                )),
            ],
            options={'ordering': ['created_at', 'pk']},
        ),
        migrations.CreateModel(
            name='ProcessAIProcessingReadiness',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purpose', models.CharField(default='investigation_questions', max_length=50)),
                ('source_rights_reviewed', models.BooleanField(default=False)),
                ('privacy_reviewed', models.BooleanField(default=False)),
                ('provider_terms_reviewed', models.BooleanField(default=False)),
                ('authorises_external_transfer', models.BooleanField(default=False, editable=False)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('analysis', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='ai_processing_readiness', to='api.processanalysisrun',
                )),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='process_ai_readiness', to='gold_intelligence.goldproject',
                )),
                ('recorded_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='recorded_ai_processing_readiness', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at', '-pk']},
        ),
    ]
