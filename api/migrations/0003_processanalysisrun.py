"""Project-scoped, minimal CSV process analysis history (no uploaded file storage)."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0002_apiscope_apikey_environment_and_more'),
        ('gold_intelligence', '0009_goldcadastresnapshot'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessAnalysisRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('case_id', models.CharField(max_length=96)),
                ('domain', models.CharField(max_length=40)),
                ('process_name', models.CharField(max_length=128)),
                ('resource_type', models.CharField(max_length=32)),
                ('period', models.CharField(max_length=7)),
                ('unit', models.CharField(max_length=128)),
                ('file_fingerprint', models.CharField(editable=False, max_length=64)),
                ('summary', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='process_analysis_runs', to=settings.AUTH_USER_MODEL,
                )),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='process_analysis_runs', to='gold_intelligence.goldproject',
                )),
            ],
            options={
                'ordering': ['-created_at', '-pk'],
                'indexes': [
                    models.Index(fields=['project', '-created_at'], name='api_process_project_time_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=('project', 'file_fingerprint'), name='unique_project_process_csv_file'),
                ],
            },
        ),
    ]
