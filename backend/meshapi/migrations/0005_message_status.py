from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meshapi', '0004_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='client_id',
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='status',
            field=models.CharField(blank=True, choices=[('sending', 'sending'), ('sent', 'sent'), ('delivered', 'delivered'), ('failed', 'failed')], max_length=16, null=True),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['client_id'], name='meshapi_mes_client__idx'),
        ),
    ]

