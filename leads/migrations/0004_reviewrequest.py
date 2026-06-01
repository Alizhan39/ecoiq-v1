from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0003_newslettersignup'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',         models.CharField(max_length=200)),
                ('organisation', models.CharField(max_length=200)),
                ('email',        models.EmailField(db_index=True)),
                ('country',      models.CharField(max_length=100)),
                ('sector', models.CharField(
                    max_length=30,
                    choices=[
                        ('renewables',     'Renewables / Clean Energy'),
                        ('infrastructure', 'Infrastructure / Transport'),
                        ('oil_gas',        'Oil & Gas / Extractives'),
                        ('agriculture',    'Agriculture / Forestry'),
                        ('manufacturing',  'Manufacturing / Industry'),
                        ('finance',        'Financial Services / Banking'),
                        ('government',     'Government / Public Sector'),
                        ('development',    'Development Finance / NGO / Research'),
                        ('other',          'Other'),
                    ],
                )),
                ('request_type', models.CharField(
                    max_length=30,
                    choices=[
                        ('company_assessment',   'Company EcoIQ Assessment'),
                        ('country_intelligence', 'Country Transition Intelligence'),
                        ('investor_readiness',   'Investor Readiness Review'),
                        ('islamic_finance',      'Islamic & Ethical Finance Fit'),
                        ('project_readiness',    'Project Readiness Review'),
                        ('greenwashing_review',  'Greenwashing Risk Review'),
                    ],
                )),
                ('message', models.TextField(blank=True, help_text='Context, questions, or specific focus areas')),
                ('sustainability_report', models.FileField(
                    blank=True, null=True,
                    upload_to='review_reports/%Y/%m/',
                    help_text='PDF only · max 10 MB',
                )),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('status', models.CharField(
                    max_length=20,
                    default='new',
                    choices=[
                        ('new',       'New'),
                        ('reviewing', 'Under Review'),
                        ('contacted', 'Contacted'),
                        ('complete',  'Complete'),
                        ('declined',  'Declined'),
                    ],
                )),
                ('notes',      models.TextField(blank=True, help_text='Internal notes — not visible to the submitter')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name':        'Review Request',
                'verbose_name_plural': 'Review Requests',
                'ordering':            ['-created_at'],
            },
        ),
    ]
