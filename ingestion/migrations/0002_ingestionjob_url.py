from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ingestionjob',
            name='url',
            field=models.URLField(blank=True, help_text='Optional: company website or document URL to seed the search'),
        ),
    ]
